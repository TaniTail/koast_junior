import asyncio
import os
import random
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

# 다운로드 폴더 설정
DOWNLOAD_FOLDER = os.path.abspath("downloads")
MTIS_URL = "https://mtis.komsa.or.kr/stg/traffic/liveSea"  #  URL 명확히 지정

async def is_ip_blocked(page):
    """서버 응답 상태 코드 확인 (429 Too Many Requests)"""
    response = await page.request.get(MTIS_URL)
    if response.status == 429:
        retry_after = response.headers.get("Retry-After", "60")
        print(f" 서버가 차단됨! {retry_after}초 후 다시 시도.")
        await asyncio.sleep(int(retry_after) + 5)
        return True
    return False

async def download_traffic_data(page, date_time):
    """실제 데이터 다운로드를 수행하는 함수"""
    print(f" {date_time} 데이터 다운로드 중...")

    #  페이지 이동 확인
    await page.goto(MTIS_URL)
    print(f" {MTIS_URL} 로 이동 완료.")

    # 3. 날짜 입력 필드 (`id="trafficVolumeDateTime"`)
    date_input_selector = "#trafficVolumeDateTime"
    await page.wait_for_selector(date_input_selector, timeout=10000)

    #  기존 텍스트 지우기 후 입력
    await page.click(date_input_selector)
    await page.press(date_input_selector, "Control+A")
    await page.press(date_input_selector, "Backspace")
    await page.fill(date_input_selector, date_time)

    # 4. 결과조회 버튼 클릭
    search_button_selector = "button.btn_search.pannel02_02_submit"
    await page.wait_for_selector(search_button_selector, timeout=10000)
    await page.click(search_button_selector)
    await asyncio.sleep(3)

    #  5. 다운로드 버튼 찾기
    download_button_selector = "button:has-text('엑셀다운')"

    #  다운로드 버튼이 나타날 때까지 기다리기
    try:
        await page.wait_for_selector(download_button_selector, timeout=15000)
    except:
        print(f"❌ 데이터 없음: {date_time} (파일 없음)")
        return

    # 다운로드 버튼이 실제로 보이는지 확인
    while not await page.locator(download_button_selector).is_visible():
        print(f"⏳ 다운로드 버튼 활성화 대기 중... ({date_time})")
        await asyncio.sleep(1)

    # 다운로드 버튼 클릭 및 파일 다운로드 대기
    async with page.expect_download(timeout=60000) as download_info:
        await page.click(download_button_selector)
    download = await download_info.value

    #  6. 파일 저장
    filename = f"교통량_{date_time.replace(' ', '_').replace(':', '')}.xlsx"
    file_path = os.path.join(DOWNLOAD_FOLDER, filename)
    await download.save_as(file_path)

    print(f"✅ 다운로드 완료: {file_path}")

async def run_all():
    async with async_playwright() as p:
        # ✅ Playwright 실행 시 옵션 추가 (자동화 탐지 회피)
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(
            accept_downloads=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # 사이트 접속 테스트
        await page.goto(MTIS_URL)
        print(f" 사이트 정상적으로 로드됨: {MTIS_URL}")

        # 시작 날짜 (2023년 2월 1일 00:00)
        start_date = datetime(2023, 5, 1, 0, 0)
        # 종료 날짜 (2025년 2월 20일 23:00)
        end_date = datetime(2025, 2, 20, 23, 0)
        # 1시간 단위 증가
        time_delta = timedelta(hours=1)

        current_date = start_date
        request_count = 0  # 요청 횟수 추적

        while current_date <= end_date:
            # 'YYYY-MM-DD HH시' 형식으로 변환
            date_time_str = current_date.strftime("%Y-%m-%d %H시")

            print(f"📅 다운로드 시도: {date_time_str}")

            # 🔹 서버가 차단되었는지 확인
            if await is_ip_blocked(page):
                continue  # 제한이 풀릴 때까지 대기 후 다시 시도

            try:
                await download_traffic_data(page, date_time_str)
            except Exception as e:
                print(f"⚠️ 오류 발생 ({date_time_str}): {e}")

            # 1시간 증가
            current_date += time_delta
            request_count += 1

            #  매 50~100개 요청마다 랜덤 대기 (1~5분)
            if request_count % random.randint(50, 100) == 0:
                wait_time = random.randint(60, 300)  # 1~5분 랜덤 대기
                print(f"⏳ 서버 보호를 위해 {wait_time}초 대기 중...")
                await asyncio.sleep(wait_time)

            #  10시간마다 5~10분 랜덤 대기하여 서버 차단 방지
            if request_count % 600 == 0:
                wait_time = random.randint(300, 600)  # 5~10분 랜덤 대기
                print(f"⏳ 서버 요청 제한 방지를 위해 {wait_time}초 대기 중...")
                await asyncio.sleep(wait_time)

            # 다운로드 간 간격 설정 (2~5초 랜덤)
            await asyncio.sleep(random.randint(2, 5))

        await browser.close()

#  실행 (자동 반복 다운로드)
if __name__ == "__main__":
    asyncio.run(run_all())
