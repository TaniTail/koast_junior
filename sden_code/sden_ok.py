import asyncio
import os
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

# 다운로드 폴더 설정
DOWNLOAD_FOLDER = os.path.abspath("downloads")






async def download_traffic_data(date_time):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()

        # 🚀 1. 해양교통안전정보시스템 접속
        await page.goto("https://mtis.komsa.or.kr/stg/traffic/liveSea")

        # 🛠 2. 페이지가 완전히 로드될 때까지 대기
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(2)

        # 📆 3. 날짜 입력 필드 (`id="trafficVolumeDateTime"`)
        date_input_selector = "#trafficVolumeDateTime"
        await page.wait_for_selector(date_input_selector, timeout=10000)

        # 🔹 3-1. 기존 텍스트('실시간 정보') 지우기 후 입력
        await page.click(date_input_selector)  # 필드 활성화
        await page.press(date_input_selector, "Control+A")  # 전체 선택
        await page.press(date_input_selector, "Backspace")  # 삭제
        await page.fill(date_input_selector, date_time)  # 'YYYY-MM-DD HH시' 형식 입력

        # 🔍 4. 결과조회 버튼 클릭 (`class="btn_search pannel02_02_submit"`)
        search_button_selector = "button.btn_search.pannel02_02_submit"
        await page.wait_for_selector(search_button_selector, timeout=10000)
        await page.click(search_button_selector)
        await asyncio.sleep(3)

        # 📥 5. 다운로드 버튼 찾기 (`button` 태그 안에 "엑셀다운" 포함)
        download_button_selector = "button:has-text('엑셀다운')"

        # 🔹 5-1. 다운로드 버튼이 나타날 때까지 기다리기
        try:
            await page.wait_for_selector(download_button_selector, timeout=10000)
        except:
            print(f"❌ 데이터 없음: {date_time} (파일 없음)")
            await browser.close()
            return

        # 🔹 5-2. 다운로드 버튼이 실제로 보이는지 확인 (is_visible 사용)
        while not await page.locator(download_button_selector).is_visible():
            print(f"⏳ 다운로드 버튼 활성화 대기 중... ({date_time})")
            await asyncio.sleep(1)

        # 🔹 5-3. 다운로드 버튼 클릭 및 파일 다운로드 대기
        async with page.expect_download() as download_info:
            await page.click(download_button_selector)
        download = await download_info.value

        # 📂 6. 파일 저장
        filename = f"교통량_{date_time.replace(' ', '_').replace(':', '')}.xlsx"
        file_path = os.path.join(DOWNLOAD_FOLDER, filename)
        await download.save_as(file_path)

        print(f"✅ 다운로드 완료: {file_path}")

        # 브라우저 종료
        await browser.close()


async def run_all():
    # 시작 날짜 (2023년 1월 1일 00:00)
    start_date = datetime(2023, 2, 1, 0, 0)
    # 종료 날짜 (2025년 2월 20일 23:00)
    end_date = datetime(2025, 2, 20, 23, 0)
    # 1시간 단위 증가
    time_delta = timedelta(hours=1)

    current_date = start_date
    while current_date <= end_date:
        # 'YYYY-MM-DD HH시' 형식으로 변환
        date_time_str = current_date.strftime("%Y-%m-%d %H시")

        print(f"📅 다운로드 시도: {date_time_str}")
        try:
            await download_traffic_data(date_time_str)
        except Exception as e:
            print(f"⚠️ 오류 발생 ({date_time_str}): {e}")

        # 1시간 증가
        current_date += time_delta
        await asyncio.sleep(1)  # 서버 부담 방지 (필요 시 조절)

# 📌 실행 (자동 반복 다운로드)
if __name__ == "__main__":
    asyncio.run(run_all())
