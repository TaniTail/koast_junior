import asyncio
from langchain_ollama import OllamaLLM
import json
import time
from datetime import datetime
import os
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, asdict
import statistics

@dataclass
class TestResult:
    """테스트 결과를 저장하기 위한 데이터 클래스"""
    test_case: str
    raw_response: str
    cleaned_response: dict
    is_valid: bool
    processing_time: float
    timestamp: str
    error: Optional[str] = None

class PromptTester:
    def __init__(self):
        # 결과 저장을 위한 디렉토리 생성
        self.results_dir = "prompt_test_results"
        os.makedirs(self.results_dir, exist_ok=True)
        
        # 테스트 결과 수집을 위한 리스트
        self.test_results: List[TestResult] = []
        
        self.llm = OllamaLLM(
            model="exaone3.5:32b",
            temperature=0.1,
            base_url='http://183.101.208.30:63001',
            retry_on_failure=True,
            num_retries=3
        )
        
        # 테스트할 프롬프트 템플릿
        self.prompt_template = """
당신은 해양 사고 음성 신고를 분석하는 전문가입니다. 
음성을 텍스트로 변환한 내용에서 구조 작업에 필요한 핵심 정보를 추출해야 합니다.

[입력 텍스트]
{text}

[분석 지침]
1. 핵심 정보 식별
   - 사고의 기본 정보(사고명, 유형, 선박명)를 먼저 파악하세요
   - 시간과 위치 정보는 최대한 정확하게 포착하세요
   - 인명 관련 정보는 가장 높은 우선순위로 처리하세요

2. 데이터 표준화
   시간: YYYY-MM-DD HH:mm:ss (24시간제)
   위치: 위도/경도 (소수점 4자리)
   숫자: 모두 아라비아 숫자로 변환 ('삼백오십' → 350)

3. 인원 분류
   다음 기준으로 승선인원을 분류하여 ID로 변환:
   89: 구명조끼 미착용 익수자
   90: 구명조끼 착용 익수자
   91: 낚시어선 인원
   46: 전복된 어선 인원
   7:  구명정 인원
   67: 위성뜰개부이 관련
   48: 레저보트 인원

[필수 응답 필드]
{
    "incidentName": "신고된 사고명 그대로",
    "incidentType": "사고 유형(화재/구조/응급의료 등)",
    "shipName": "선박명(반드시 '호'로 끝나야 함)",
    "lastknownDate": "최종 교신 시각",
    "lastknownPosition": {
        "latitude": "위도",
        "longitude": "경도"
    },
    "personOnboard": [해당하는 인원 ID를 인원수만큼 배열로],
    "description": "중복 없는 핵심 정보 요약"
}

[주의사항]
- 발음이 부정확할 수 있으므로 문맥을 고려하여 해석하세요
- 불확실한 정보는 포함하지 마세요
- 모든 응답은 JSON 형식으로만 제공하세요
- JSON 외의 추가 텍스트는 포함하지 마세요
"""
        
        # 테스트 케이스들
        self.test_cases = [
            "여기는 울릉도 앞바다입니다. 현재 낚시어선 드림호가 조난 신호를 보냈습니다. 승선인원은 10명이고 구명조끼는 착용했습니다.",
            "저는 제주 해경입니다. 오늘 오후 3시경에 한라호에서 화재가 발생했다는 신고가 들어왔습니다. 현재 승선원 3명이 구명정에 탑승했고, 2명은 구명조끼 없이 바다에 있습니다.",
            "경상북도 포항 앞바다에서 어선 충돌 사고가 발생했습니다. 태양호가 침몰 중이며 승선원 5명 중 3명은 구명조끼를 입고 구조를 기다리고 있고, 2명은 행방불명 상태입니다."
        ]

    def _clean_response(self, response: str) -> str:
        """LLM 응답에서 JSON 부분을 추출하고 정제"""
        try:
            start = response.find("{")
            end = response.rfind("}")
            if start != -1 and end != -1:
                json_str = response[start:end + 1]
                json_str = json_str.replace('\\"', '"').replace("\\'", "'")
                json_str = json_str.replace('\\n', ' ').replace('\n', ' ')
                return ' '.join(json_str.split())
            return response
        except Exception as e:
            print(f"정제 오류: {e}")
            return response

    def _validate_response(self, data: dict) -> bool:
        """응답 데이터의 구조와 형식을 검증"""
        try:
            required_fields = {'incidentName', 'incidentType', 'shipName'}
            if not all(field in data for field in required_fields):
                return False
            
            if 'personOnboard' in data:
                valid_ids = {7, 46, 48, 67, 89, 90, 91}
                if not all(isinstance(id_, int) and id_ in valid_ids 
                          for id_ in data['personOnboard']):
                    return False
            
            if 'lastknownPosition' in data:
                pos = data['lastknownPosition']
                if not (isinstance(pos, dict) and 
                       'latitude' in pos and 'longitude' in pos):
                    return False
            
            return True
            
        except Exception as e:
            print(f"검증 오류: {e}")
            return False

    def save_test_results(self) -> str:
        """모든 테스트 결과를 JSON 파일로 저장"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = os.path.join(self.results_dir, f"test_results_{timestamp}.json")
        
        # 전체 테스트 통계 계산
        processing_times = [result.processing_time for result in self.test_results]
        valid_responses = sum(1 for result in self.test_results if result.is_valid)
        
        summary = {
            "timestamp": timestamp,
            "total_tests": len(self.test_results),
            "successful_validations": valid_responses,
            "average_processing_time": statistics.mean(processing_times),
            "max_processing_time": max(processing_times),
            "min_processing_time": min(processing_times),
            "individual_results": [asdict(result) for result in self.test_results]
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
            
        return filename

    def print_test_summary(self) -> None:
        """테스트 결과 요약을 콘솔에 출력"""
        total_tests = len(self.test_results)
        valid_responses = sum(1 for result in self.test_results if result.is_valid)
        processing_times = [result.processing_time for result in self.test_results]
        
        print("\n" + "="*50)
        print("테스트 결과 요약")
        print("="*50)
        print(f"총 테스트 케이스: {total_tests}")
        print(f"성공적인 검증: {valid_responses}")
        print(f"평균 처리 시간: {statistics.mean(processing_times):.2f}초")
        print(f"최대 처리 시간: {max(processing_times):.2f}초")
        print(f"최소 처리 시간: {min(processing_times):.2f}초")
        print("="*50)

    async def test_prompt(self, text: str) -> None:
        """단일 테스트 케이스 실행"""
        start_time = time.time()
        error_msg = None
        
        try:
            print("\n=== 테스트 입력 ===")
            print(text)
            print("\n=== 프롬프트 처리 중 ===")
            
            response = await self.llm.ainvoke(
                self.prompt_template.format(text=text)
            )
            
            cleaned_response = self._clean_response(response)
            print("\n=== 원본 응답 ===")
            print(response)
            
            try:
                parsed_data = json.loads(cleaned_response)
                print("\n=== 정제된 응답 ===")
                print(json.dumps(parsed_data, ensure_ascii=False, indent=2))
                
                is_valid = self._validate_response(parsed_data)
                print(f"\n응답 유효성: {'성공' if is_valid else '실패'}")
                
            except json.JSONDecodeError as e:
                print("\n=== JSON 파싱 실패 ===")
                print(cleaned_response)
                parsed_data = {}
                is_valid = False
                error_msg = f"JSON 파싱 오류: {str(e)}"
                
        except Exception as e:
            print(f"\n오류 발생: {e}")
            response = ""
            parsed_data = {}
            is_valid = False
            error_msg = str(e)
            
        finally:
            end_time = time.time()
            processing_time = end_time - start_time
            print(f"\n처리 시간: {processing_time:.2f}초")
            
            # 테스트 결과 저장
            result = TestResult(
                test_case=text,
                raw_response=response,
                cleaned_response=parsed_data,
                is_valid=is_valid,
                processing_time=processing_time,
                timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                error=error_msg
            )
            self.test_results.append(result)

    async def run_all_tests(self) -> None:
        """모든 테스트 케이스 실행"""
        for i, test_case in enumerate(self.test_cases, 1):
            print(f"\n{'='*50}")
            print(f"테스트 케이스 #{i}")
            print('='*50)
            await self.test_prompt(test_case)
        
        # 테스트 결과 저장 및 요약 출력
        results_file = self.save_test_results()
        self.print_test_summary()
        print(f"\n상세 테스트 결과가 저장된 파일: {results_file}")

async def main():
    tester = PromptTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())