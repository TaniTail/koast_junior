# 필요한 라이브러리 임포트
import signal
import sys
import asyncio
import websockets
import whisper
import numpy as np
import soundfile as sf
import base64
import json
import tempfile
import subprocess
import os
import logging
import ssl
import torch
import time
import aiohttp
from datetime import datetime
from dotenv import load_dotenv
import noisereduce as nr
from langchain_ollama import OllamaLLM
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

# 환경 변수 로드 및 로깅 설정
load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 환경 변수에서 서버 설정 로드
WS_HOST = os.getenv('WS_HOST')
IN_WS_PORT = int(os.getenv('IN_WS_PORT'))
SSL_CERT_PATH = os.getenv('SSL_CERT_PATH')
SSL_KEY_PATH = os.getenv('SSL_KEY_PATH')
WHISPER_MODEL = os.getenv('WHISPER_MODEL')
FFMPEG_SAMPLE_RATE = os.getenv('FFMPEG_SAMPLE_RATE')
FFMPEG_CHANNELS = os.getenv('FFMPEG_CHANNELS')
WHISPER_MODEL_PATH = os.getenv('WHISPER_MODEL_PATH')

# 타임아웃 설정
AUDIO_PROCESSING_TIMEOUT = 30  # 오디오 처리 타임아웃 (초)
LLM_TIMEOUT = 30  # LLM 처리 타임아웃 (초)

@dataclass
class ClientState:
    """클라이언트별 상태를 관리하는 클래스"""
    websocket: websockets.WebSocketServerProtocol
    accumulated_text: List[str]  # 누적된 음성 인식 텍스트
    last_activity: float  # 마지막 활동 시간

    def __init__(self, websocket):
        self.websocket = websocket
        self.accumulated_text = []
        self.last_activity = time.time()


class TextAnalyzer:
    """
    음성 텍스트를 분석하고 구조화된 정보로 변환하는 클래스입니다.
    
    이 클래스는 해양 사고 관련 음성 신고를 처리하고, 구조화된 JSON 형식으로 변환하는 역할을 합니다.
    LLM(Large Language Model)을 사용하여 텍스트를 분석하고, 필요한 정보를 추출합니다.
    비동기 처리를 지원하며, 상세한 로깅 기능을 제공합니다.
    """
    
    def _create_log_file(self) -> str:
        """
        새로운 로그 파일을 생성하고 경로를 반환합니다.
        로그 파일은 타임스탬프를 포함한 고유한 이름으로 생성됩니다.
        
        Returns:
            str: 생성된 로그 파일의 경로
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = os.path.join(self.log_directory, f"llm_responses_{timestamp}.jsonl")
            
            # 파일 생성 가능 여부 테스트
            with open(log_file, 'a') as f:
                f.write("")
            
            logger.info(f"Created log file: {log_file}")
            return log_file
        except Exception as e:
            logger.error(f"Failed to create log file: {e}")
            # 기본 디렉토리 접근이 불가능한 경우 임시 디렉토리 사용
            return os.path.join(tempfile.gettempdir(), f"llm_responses_{timestamp}.jsonl")

    def _initialize_llm(self):
        """
        LLM(Large Language Model) 설정을 초기화합니다.
        모델의 기본 매개변수와 연결 설정을 구성합니다.
        """
        self.llm = OllamaLLM(
            model="exaone3.5:32b",
            temperature=0.1,  # 낮은 temperature로 일관된 출력 유도
            base_url='http://183.101.208.30:63001',
            retry_on_failure=True,
            num_retries=3  # 네트워크 오류에 대한 재시도 허용
        )

    def _initialize_logging(self):
        """
        로깅 시스템을 초기화합니다.
        HTTP 세션을 생성하고 로그 파일을 설정합니다.
        """
        self.session = aiohttp.ClientSession()
        self.log_directory = os.getenv('LOG_DIRECTORY', '/app/llm_logs')
        self.log_file_path = self._create_log_file()

    def _initialize_prompt_template(self):
        """
        프롬프트 템플릿을 초기화합니다.
        LLM에 전달될 기본 프롬프트 구조를 설정합니다.
        """
        self.prompt_template = (
            "당신은 해양 사고 음성 신고를 분석하는 전문가입니다.\n"
            "음성을 텍스트로 변환한 내용에서 구조 작업에 필요한 핵심 정보를 추출하고,\n"
            "발음이 부정확할 수 있으므로 문맥에 따라 수색구조에 적절한 단어로 해석해주세요.\n"
            "특히 알파벳은 문맥에 맞게 해석합니다.\n\n"
            
            "[입력 텍스트]\n"
            "{input_text}\n\n"
            
            "[필수 필드 구성]\n"
            "1. type: 항상 \"INCIDENT\"로 고정\n"
            "2. property: 다음 필드들로만 구성된 객체\n"
            "   - incidentName: 신고자가 언급한 사고명\n"
            "   - incidentType: 화재, 구조, 인명사상, 침몰, 충돌 등 사고 유형\n"
            "   - shipName: 선박명 ('호'로 끝나야 함)\n"
            "   - lastknownDate: 최종 교신 시각 (YYYY-MM-DD HH:mm:ss)\n"
            "   - lastknownPosition: 위치 정보 객체 {{latitude(위도), longitude(경도)}}\n"
            "   - reportedDate: 신고 접수 시각 (YYYY-MM-DD HH:mm:ss)\n"
            "   - shipCode: 선박 코드 종류 (MMSI, IMO, RFID 중 하나)\n"
            "   - shipId: 선박 코드 번호 (숫자만)\n"
            "   - personOnboard: 승선인원 ID 배열\n"
            "   - description: 핵심 정보 요약\n"
            "3. task: 다음 중 하나 선택\n"
            "   - enter: 기본값. 사고 등록 진행 중이거나 유의미한 정보가 있는 경우\n"
            "   - run: 다음 키워드 포함 시 (사고등록을 마칩니다/완료합니다/종료합니다, 등록을 마치겠습니다, 완료하겠습니다)\n"
            "   - cancel: 다음 키워드 포함 시 (취소, 등록을 취소, 중단)\n\n"
            
            "[핵심 규칙]\n"
            "1. 승선인원 ID 매핑:\n"
            "   - 89: 구명조끼 미착용 익수자\n"
            "   - 90: 구명조끼 착용 익수자\n"
            "   - 91: 낚시어선 인원\n"
            "   - 46: 전복된 어선 인원\n"
            "   - 7: 구명정 인원\n"
            "   - 67: 위성뜰개부이 관련\n"
            "   - 48: 레저보트 인원\n"
            "2. 데이터 처리:\n"
            "   - 모든 숫자는 아라비아 숫자로 변환\n"
            "   - 시간은 24시간제 사용\n"
            "   - 위치 좌표는 소수점 4자리까지 표시\n"
            "   - 확실한 정보만 포함 (불확실한 정보는 필드 제외)\n"
            "   - 언급되지 않은 사고명/유형은 필드 자체를 제외\n\n"

            "[응답 예시]\n"
            "{{\n"
            "    \"type\": \"INCIDENT\",\n"
            "    \"property\": {{\n"
            "        \"incidentName\": \"거제 씨프린스호 화재사고\",\n"
            "        \"incidentType\": \"화재\",\n"
            "        \"lastknownDate\": \"2024-01-17 14:30:00\",\n"
            "        \"lastknownPosition\": {{\n"
            "            \"longitude\": 127.4639,\n"
            "            \"latitude\": 33.9444\n"
            "        }},\n"
            "        \"reportedDate\": \"2024-01-17 15:00:00\",\n"
            "        \"shipName\": \"씨프린스호\",\n"
            "        \"shipCode\": \"MMSI\",\n"
            "        \"shipId\": 298797,\n"
            "        \"personOnboard\": [89, 89, 90, 46, 46, 46],\n"
            "        \"description\": \"엔진실에서 발생, 자체 진화 실패\"\n"
            "    }},\n"
            "    \"task\": \"enter\"\n"
            "}}\n\n"
            
            "유효한 JSON 형식으로만 응답하고, 다른 텍스트는 포함하지 마세요."
        )

    def __init__(self):
        """
        TextAnalyzer 클래스를 초기화합니다.
        LLM, 로깅 시스템, 프롬프트 템플릿을 순차적으로 설정합니다.
        """
        try:
            self._initialize_llm()
            self._initialize_logging()
            self._initialize_prompt_template()
            
            logger.info("TextAnalyzer initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize TextAnalyzer: {e}")
            raise

    async def analyze_text(self, text: str) -> dict:
        """
        입력된 텍스트를 분석하여 구조화된 정보를 추출합니다.
        
        Args:
            text (str): 분석할 입력 텍스트
            
        Returns:
            dict: 분석 결과를 담은 구조화된 딕셔너리
        """
        try:
            # 입력 검증
            if not isinstance(text, str):
                logger.error(f"Invalid input type: {type(text)}")
                return self._create_error_response("잘못된 입력 형식")
                
            if not text.strip():
                logger.error("Empty input text")
                return self._create_error_response("빈 입력")
            
            # 텍스트 전처리
            text = text.strip()
            text = text.replace('"', '\\"')  # JSON 문자열 이스케이프 처리
            
            logger.info(f"Analyzing text (length: {len(text)})")
            logger.debug(f"Processing text: {text[:100]}...")
            
            # LLM에 요청 전송
            formatted_prompt = self.prompt_template.format(input_text=text)
            
            # 프롬프트 로깅
            logger.debug("Formatted prompt:")
            logger.debug(formatted_prompt)
            
            # LLM 호출 및 타임아웃 처리
            raw_response = await asyncio.wait_for(
                loop.run_in_executor(
                    None, 
                    lambda: self.llm.invoke(formatted_prompt)
                ),
                timeout=LLM_TIMEOUT
            )
            
            # 응답 로깅
            logger.debug("Raw LLM response:")
            logger.debug(raw_response)
            
            # 응답 정제 및 처리
            cleaned_response = self._clean_llm_response(raw_response)
            await self.log_llm_interaction(text, raw_response, cleaned_response)
            
            # JSON 파싱 및 검증
            try:
                parsed_response = json.loads(cleaned_response)
                return self._validate_and_normalize_response(parsed_response)
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error: {e}")
                logger.error(f"Problematic JSON string: {cleaned_response}")
                return self._create_error_response("응답 형식 처리 오류")
                
        except asyncio.TimeoutError:
            logger.error("LLM analysis timeout")
            return self._create_error_response("분석 시간 초과")
        except Exception as e:
            logger.error(f"Analysis error: {str(e)}")
            logger.exception("상세 에러 정보:")
            return self._create_error_response("분석 중 오류 발생")

    def _clean_llm_response(self, response: str) -> str:
        """
        LLM의 응답을 정제하여 유효한 JSON으로 변환합니다.
        
        Args:
            response (str): LLM의 원본 응답
            
        Returns:
            str: 정제된 JSON 문자열
        """
        try:
            logger.debug("Original LLM response:")
            logger.debug(response)
            
            # 문자열 정제
            cleaned = response.strip()
            
            # JSON 객체의 시작과 끝 위치 찾기
            start_idx = cleaned.find('{')
            end_idx = cleaned.rfind('}')
            
            if start_idx == -1 or end_idx == -1:
                logger.warning("No valid JSON structure found in response")
                return self._create_default_json()
                
            # JSON 부분만 추출
            json_str = cleaned[start_idx:end_idx + 1]
            
            # 여러 줄의 문자열을 단일 줄로 변환하고 불필요한 공백 제거
            json_str = ' '.join(
                line.strip() 
                for line in json_str.splitlines() 
                if line.strip()
            )
            
            # 정제된 JSON 문자열 파싱 시도
            try:
                parsed_json = json.loads(json_str)
                # 필수 필드 확인 및 보완
                if not isinstance(parsed_json, dict):
                    return self._create_default_json()
                    
                if "type" not in parsed_json:
                    parsed_json["type"] = "INCIDENT"
                if "task" not in parsed_json:
                    parsed_json["task"] = "enter"
                if "property" not in parsed_json:
                    parsed_json["property"] = {}
                    
                return json.dumps(parsed_json, ensure_ascii=False)
                
            except json.JSONDecodeError:
                logger.error("Failed to parse cleaned JSON string")
                return self._create_default_json()
                
        except Exception as e:
            logger.error(f"Error in response cleaning: {str(e)}")
            return self._create_default_json()

    def _validate_and_normalize_response(self, response: dict) -> dict:
        """
        응답의 구조를 검증하고 정규화합니다.
        
        Args:
            response (dict): 검증할 응답 딕셔너리
            
        Returns:
            dict: 정규화된 응답 딕셔너리
        """
        try:
            normalized = {
                "type": "INCIDENT",
                "task": "enter",
                "property": {}
            }
            
            if isinstance(response, dict):
                if "type" in response:
                    normalized["type"] = response["type"]
                
                if "task" in response and response["task"] in ["enter", "run", "cancel"]:
                    normalized["task"] = response["task"]
                
                if "property" in response and isinstance(response["property"], dict):
                    normalized["property"] = {
                        k: v for k, v in response["property"].items()
                        if v is not None and v != ""
                    }
            
            return normalized
            
        except Exception as e:
            logger.error(f"Error in response validation: {e}")
            return self._create_error_response("응답 검증 오류")

    async def log_llm_interaction(self, input_text: str, raw_response: str, cleaned_response: str):
        """
        LLM과의 상호작용을 로그 파일에 기록합니다.
        
        Args:
            input_text (str): 입력 텍스트
            raw_response (str): LLM의 원본 응답
            cleaned_response (str): 정제된 응답
        """
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "input_text": input_text,
                "raw_response": raw_response,
                "cleaned_response": cleaned_response
            }
            
            if not os.path.exists(os.path.dirname(self.log_file_path)):
                logger.warning(f"Log directory does not exist: {os.path.dirname(self.log_file_path)}")
                return
                
            try:
                async with aiofiles.open(self.log_file_path, mode='a', encoding='utf-8') as f:
                    await f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
                    await f.flush()
                    
                logger.debug(f"Successfully logged interaction to {self.log_file_path}")
                
            except Exception as write_error:
                logger.error(f"Failed to write to log file: {write_error}")
                
        except Exception as e:
            logger.error(f"Failed to log LLM interaction: {e}")

    def _create_default_json(self) -> str:
        """
        기본 JSON 응답을 생성합니다.
        
        Returns:
            str: 기본 JSON 응답 문자열
        """
        return json.dumps({
            "type": "INCIDENT",
            "property": {},
            "task": "enter"
        }, ensure_ascii=False)

    def _create_error_response(self, message: str) -> dict:
        """
        에러 상황에 대한 응답을 생성합니다.
        
        표준화된 에러 응답 형식을 사용하여 일관된 에러 처리를 보장합니다.
        status와 message 필드를 포함하여 에러의 원인을 명확히 전달합니다.
        
        Args:
            message (str): 에러 상황을 설명하는 메시지
            
        Returns:
            dict: 에러 정보를 포함한 응답 딕셔너리
        """
        return {
            "type": "INCIDENT",
            "property": {
                "status": "error",
                "message": message
            },
            "task": "enter"
        }

    def _identify_error_pattern(self, raw_response: str) -> str:
        """
        LLM 응답에서 발생한 에러 패턴을 식별합니다.
        
        여러 가지 일반적인 에러 패턴을 검사하여 문제의 원인을 파악합니다.
        이 정보는 로깅과 디버깅에 활용됩니다.
        
        Args:
            raw_response (str): 분석할 원본 응답
            
        Returns:
            str: 식별된 에러 패턴의 설명
        """
        if not raw_response.strip():
            return "empty_response"
        if raw_response.count('{') != raw_response.count('}'):
            return "unmatched_braces"
        if '\n' in raw_response:
            return "contains_newlines"
        if '"' not in raw_response:
            return "missing_quotes"
        return "other"

    async def analyze_logs(self) -> dict:
        """
        로그 파일을 분석하여 시스템 성능과 오류 패턴을 파악합니다.
        
        로그 파일에서 다양한 통계 정보를 추출하여 시스템의 동작을 모니터링하고
        잠재적인 문제점을 식별하는 데 도움을 줍니다.
        
        Returns:
            dict: 분석된 통계 정보를 담은 딕셔너리
        """
        try:
            stats = {
                "total_interactions": 0,
                "successful_parses": 0,
                "failed_parses": 0,
                "common_error_patterns": {},
                "response_lengths": [],
                "average_processing_time": 0
            }
            
            processing_times = []
            
            async with aiofiles.open(self.log_file_path, mode='r', encoding='utf-8') as f:
                async for line in f:
                    entry = json.loads(line)
                    stats["total_interactions"] += 1
                    stats["response_lengths"].append(len(entry["raw_response"]))
                    
                    try:
                        json.loads(entry["cleaned_response"])
                        stats["successful_parses"] += 1
                    except json.JSONDecodeError:
                        stats["failed_parses"] += 1
                        error_pattern = self._identify_error_pattern(entry["raw_response"])
                        stats["common_error_patterns"][error_pattern] = \
                            stats["common_error_patterns"].get(error_pattern, 0) + 1
                    
                    if "timestamp" in entry:
                        processing_time = self._calculate_processing_time(entry)
                        if processing_time:
                            processing_times.append(processing_time)
            
            if processing_times:
                stats["average_processing_time"] = sum(processing_times) / len(processing_times)
            
            self._log_analysis_results(stats)
            return stats
            
        except Exception as e:
            logger.error(f"Failed to analyze logs: {e}")
            return None

    def _calculate_processing_time(self, log_entry: dict) -> float:
        """
        로그 엔트리의 처리 시간을 계산합니다.
        
        현재는 단순 구현이지만, 필요한 경우 시작/종료 시간을 추가하여
        더 정확한 처리 시간 계산이 가능하도록 확장할 수 있습니다.
        
        Args:
            log_entry (dict): 처리 시간을 계산할 로그 엔트리
            
        Returns:
            float: 처리 시간(초)
        """
        try:
            timestamp = datetime.fromisoformat(log_entry["timestamp"])
            return 0.0  # 현재는 더미 값 반환, 향후 실제 처리 시간 계산 구현 가능
        except Exception:
            return 0.0

    def _log_analysis_results(self, stats: dict):
        """
        분석 결과를 로그에 기록합니다.
        
        통계 정보를 체계적으로 로깅하여 시스템 모니터링과
        성능 분석에 활용할 수 있도록 합니다.
        
        Args:
            stats (dict): 로깅할 분석 통계 정보
        """
        logger.info("Log Analysis Results:")
        logger.info(f"Total Interactions: {stats['total_interactions']}")
        logger.info(f"Successful Parses: {stats['successful_parses']}")
        logger.info(f"Failed Parses: {stats['failed_parses']}")
        logger.info("Common Error Patterns:")
        
        for pattern, count in stats["common_error_patterns"].items():
            logger.info(f"  - {pattern}: {count}")
        
        if stats["response_lengths"]:
            avg_length = sum(stats["response_lengths"]) / len(stats["response_lengths"])
            logger.info(f"Average Response Length: {avg_length:.2f}")
        
        if stats["average_processing_time"]:
            logger.info(f"Average Processing Time: {stats['average_processing_time']:.2f}s")

    async def __aenter__(self):
        """비동기 컨텍스트 매니저의 진입점입니다."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        비동기 컨텍스트 매니저의 종료점입니다.
        리소스 정리를 보장합니다.
        """
        await self.cleanup()

    async def cleanup(self):
        """
        클래스의 리소스를 정리합니다.
        
        세션과 같은 비동기 리소스들을 안전하게 정리하여
        메모리 누수를 방지하고 리소스를 적절히 해제합니다.
        """
        try:
            if hasattr(self, 'session') and not self.session.closed:
                await self.session.close()
                logger.info("Successfully closed client session")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")




class AudioProcessor:
    """오디오 처리를 담당하는 클래스"""
    def __init__(self):
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.setup_gpu()
        self.load_model()

    def setup_gpu(self):
        """GPU 설정 초기화"""
        if self.device == "cuda":
            logger.info("Using GPU acceleration")
            torch.cuda.empty_cache()
            torch.cuda.set_per_process_memory_fraction(0.8)
        else:
            logger.warning("Using CPU")

    def load_model(self):
        """Whisper 모델 로드"""
        try:
            logger.info(f"Loading Whisper model: {WHISPER_MODEL}")
            self.model = whisper.load_model(WHISPER_MODEL, download_root=WHISPER_MODEL_PATH)
            logger.info("Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise

    async def process_audio(self, audio_bytes: bytes) -> str:
        """오디오 처리를 비동기적으로 수행"""
        try:
            with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_webm:
                temp_webm.write(audio_bytes)
                temp_webm_path = temp_webm.name

            temp_wav_path = temp_webm_path + '.wav'
            
            try:
                await self.convert_audio(temp_webm_path, temp_wav_path)
                audio_array = await self.load_audio(temp_wav_path)
                enhanced_audio = await self.enhance_audio(audio_array)
                
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, 
                    lambda: self.model.transcribe(enhanced_audio)
                )
                
                return result['text']
                
            finally:
                # 임시 파일 정리
                for path in [temp_webm_path, temp_wav_path]:
                    try:
                        if os.path.exists(path):
                            os.unlink(path)
                    except Exception as e:
                        logger.error(f"Failed to delete temporary file {path}: {e}")
                        
        except Exception as e:
            logger.error(f"Error in audio processing: {e}")
            raise

    async def convert_audio(self, input_path: str, output_path: str):
        """오디오 변환을 비동기적으로 수행"""
        process = await asyncio.create_subprocess_exec(
            'ffmpeg', '-i', input_path,
            '-ar', FFMPEG_SAMPLE_RATE,
            '-ac', FFMPEG_CHANNELS,
            '-y', output_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.error(f"FFmpeg error: {stderr.decode()}")
            raise Exception("FFmpeg conversion failed")

    async def load_audio(self, path: str) -> np.ndarray:
        """오디오 파일 로드를 비동기적으로 수행"""
        loop = asyncio.get_event_loop()
        audio_array, _ = await loop.run_in_executor(None, sf.read, path)
        return audio_array.astype(np.float32)

    async def enhance_audio(self, audio_array: np.ndarray) -> np.ndarray:
        """오디오 품질 개선을 비동기적으로 수행"""
        try:
            if torch.cuda.is_available():
                current_memory = torch.cuda.memory_allocated()
                total_memory = torch.cuda.get_device_properties(0).total_memory
                if current_memory > 0.9 * total_memory:
                    torch.cuda.empty_cache()
                    logger.warning("GPU memory cleared due to high usage")

            loop = asyncio.get_event_loop()
            enhanced = await loop.run_in_executor(
                None,
                lambda: nr.reduce_noise(
                    y=audio_array,
                    sr=16000,
                    stationary=True,
                    prop_decrease=0.60,
                    n_fft=1024,
                    win_length=1024,
                    hop_length=256,
                    use_torch=True,
                    device=self.device
                )
            )
            return enhanced
        except Exception as e:
            logger.error(f"Error in audio enhancement: {e}")
            return audio_array


class WebSocketServer:
    """웹소켓 서버 클래스"""
    def __init__(self):
        self.connected_clients: Dict[websockets.WebSocketServerProtocol, ClientState] = {}
        self.text_analyzer = None
        self.audio_processor = None
        self.progress_markers = ["진행", "다음", "오케이", "확인", "넘어가기"]

    async def initialize(self):
        """서버 컴포넌트 초기화"""
        self.text_analyzer = TextAnalyzer()
        self.audio_processor = AudioProcessor()

    async def cleanup(self):
        """서버 리소스 정리"""
        if self.text_analyzer:
            await self.text_analyzer.cleanup()

    async def handle_client(self, websocket: websockets.WebSocketServerProtocol):
        """클라이언트 연결 처리"""
        client_state = ClientState(websocket)
        self.connected_clients[websocket] = client_state
        
        try:
            logger.info(f"New client connected. Total clients: {len(self.connected_clients)}")
            async for message in websocket:
                await self.process_message(client_state, message)
        except websockets.exceptions.ConnectionClosed:
            logger.info("Client connection closed normally")
        except Exception as e:
            logger.error(f"Error handling client: {e}")
        finally:
            del self.connected_clients[websocket]
            logger.info(f"Client disconnected. Remaining clients: {len(self.connected_clients)}")

    async def process_message(self, client_state: ClientState, message: str):
        """클라이언트 메시지 처리"""
        try:
            start_time = time.time()
            data = json.loads(message)
            
            # 처리 시작 메시지
            await client_state.websocket.send(json.dumps({
                "message": "오디오 처리 시작..."
            }))

            audio_data = data['audio']
            audio_bytes = base64.b64decode(audio_data.split(',')[1])
            
            # 오디오 처리를 비동기 함수로 래핑
            async def process_audio_wrapper():
                text = await self.audio_processor.process_audio(audio_bytes)
                return text

            text = await asyncio.wait_for(
                process_audio_wrapper(),
                timeout=AUDIO_PROCESSING_TIMEOUT
            )
            
            if text:
                # 진행 마커 확인
                found_marker = any(marker in text for marker in self.progress_markers)
                
                if found_marker:
                    current_text = text.split(
                        next((m for m in self.progress_markers if m in text), "")
                    )[0].strip()
                else:
                    current_text = text
                
                if current_text:
                    client_state.accumulated_text.append(current_text)
                
                if found_marker and client_state.accumulated_text:
                    # 최종 분석 결과는 기존 포맷 유지
                    full_text = " ".join(client_state.accumulated_text)
                    analysis_result = await self.text_analyzer.analyze_text(full_text)
                    await client_state.websocket.send(json.dumps(
                        analysis_result,
                        ensure_ascii=False
                    ))
                    client_state.accumulated_text = []
                else:
                    await client_state.websocket.send(json.dumps({
                        "message": text
                    }, ensure_ascii=False))
            
            client_state.last_activity = time.time()
            
        except asyncio.TimeoutError:
            logger.error("Audio processing timeout")
            await client_state.websocket.send(json.dumps({
                "message": "처리 시간 초과"
            }, ensure_ascii=False))
        
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            await client_state.websocket.send(json.dumps({
                "message": "잘못된 메시지 형식"
            }, ensure_ascii=False))
        
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await client_state.websocket.send(json.dumps({
                "message": f"처리 중 오류 발생: {str(e)}"
            }, ensure_ascii=False))

    async def monitor_inactive_clients(self):
        """비활성 클라이언트 모니터링 및 정리"""
        while True:
            try:
                current_time = time.time()
                inactive_clients = [
                    client for client, state in self.connected_clients.items()
                    if current_time - state.last_activity > 300  # 5분 타임아웃
                ]
                
                for client in inactive_clients:
                    try:
                        await client.close()
                        logger.info(f"Closed inactive client connection")
                    except Exception as e:
                        logger.error(f"Error closing inactive client: {e}")
                
                await asyncio.sleep(60)  # 1분마다 체크
                
            except Exception as e:
                logger.error(f"Error in client monitoring: {e}")
                await asyncio.sleep(60)

async def shutdown(loop, signal=None):
    """서버 종료 처리"""
    if signal:
        logger.info(f"Received exit signal {signal.name}")
    
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    
    for task in tasks:
        task.cancel()
    
    logger.info(f"Cancelling {len(tasks)} outstanding tasks")
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()

async def main():
    """메인 서버 실행 함수"""
    try:
        # SSL 컨텍스트 설정
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(SSL_CERT_PATH, SSL_KEY_PATH)
        
        # 서버 인스턴스 생성 및 초기화
        server = WebSocketServer()
        await server.initialize()
        
        # 비활성 클라이언트 모니터링 태스크 시작
        monitoring_task = asyncio.create_task(server.monitor_inactive_clients())
        
        logger.info(f"Starting WebSocket server on {WS_HOST}:{IN_WS_PORT}...")
        async with websockets.serve(
            server.handle_client,
            WS_HOST,
            IN_WS_PORT,
            ssl=ssl_context
        ):
            logger.info(f"WebSocket server is running on wss://{WS_HOST}:{IN_WS_PORT}")
            
            try:
                await asyncio.Future()  # 서버 실행 유지
            except asyncio.CancelledError:
                logger.info("Server shutdown initiated")
                monitoring_task.cancel()
                await server.cleanup()
                
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise

if __name__ == "__main__":
    try:
        # 시그널 핸들러 설정
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
        for s in signals:
            loop.add_signal_handler(
                s, lambda s=s: asyncio.create_task(shutdown(loop, signal=s))
            )
        
        try:
            loop.run_until_complete(main())
        finally:
            loop.close()
            logger.info("Server shutdown complete")
            
    except KeyboardInterrupt:
        logger.info("Server terminated by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        logger.exception("Detailed error information:")
        sys.exit(1)