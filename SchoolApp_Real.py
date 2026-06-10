import requests
import re
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# ---------------------------------------------------------
# 🌐 CORS 설정 (유니티나 웹에서 API 호출할 때 차단되지 않게 함)
# ---------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 모든 접근 허용 (실제 배포때는 특정 도메인만 넣어도 됨)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# ⚙️ 전역 변수 설정 (앱 상태 및 임시 DB)
# ---------------------------------------------------------
CURRENT_APP_VERSION = "1.0.0" # 현재 최신 앱 버전
MIN_REQ_VERSION = "1.0.0"     # 이 버전보다 낮으면 앱 실행 막음
IS_MAINTENANCE = False        # 🚨 이 값을 True로 바꾸고 Render에서 재시작하면 앱 차단됨!
MAINTENANCE_MSG = "현재 서버 업데이트 중입니다. 잠시만 기다려주세요! 🛠️"
GRADUATION_DATE = "2027-01-08" # 대평고 졸업식 날짜 (예시)

# 별점을 임시로 저장할 딕셔너리 (Render가 재시작되면 초기화됨. 나중에 진짜 DB로 변경 추천!)
meal_ratings_db = {}


# ---------------------------------------------------------
# 1️⃣ 기본 엔드포인트
# ---------------------------------------------------------
@app.get("/")
def read_root():
    return {"message": "절대이사이트에들어오지마"}


# ---------------------------------------------------------
# 2️⃣ [앱 컨트롤 타워] 유지보수 및 업데이트 관리 API
# ---------------------------------------------------------
@app.get("/status")
def get_app_status():
    """
    유니티 앱이 켜질 때 가장 먼저 호출해야 하는 API.
    버전 체크와 서버 점검 상태를 알려줌.
    """
    return {
        "success": True,
        "latest_version": CURRENT_APP_VERSION,
        "min_version": MIN_REQ_VERSION,
        "is_maintenance": IS_MAINTENANCE,
        "maintenance_message": MAINTENANCE_MSG,
        "notice": "이번 주 금요일 동아리 발표가 있습니다! 🎉", # 앱 메인에 띄울 공지사항
        "graduation_date": GRADUATION_DATE
    }


# ---------------------------------------------------------
# 3️⃣ 급식 조회 API
# ---------------------------------------------------------
@app.get("/meal")
def get_meal(date: str = None):
    # 날짜 설정 (안 적으면 오늘, 적으면 그 날짜)
    if not date:
        date = datetime.now().strftime("%Y%m%d")
    
    # NEIS API 설정
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    params = {
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": "J10", # 경기도 교육청
        "SD_SCHUL_CODE": "7530554",  # 대평고등학교 코드
        "MLSV_YMD": date
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        # 급식 데이터 뭉치 가져오기
        meals_row = data["mealServiceDietInfo"][1]["row"]
        
        result_meals = {}
        for row in meals_row:
            meal_type = row["MMEAL_SC_NM"] # 조식, 중식, 석식
            
            # 지저분한 메뉴 이름 다듬기 (마파두부덮밥5.6... -> 마파두부덮밥)
            raw_menu = row["DDISH_NM"]
            clean_menu = []
            for item in raw_menu.split("<br/>"):
                # 숫자, 마침표, 괄호를 지우고 글자만 남김
                food = re.sub(r'[0-9\.\(\)]', '', item).strip()
                if food:
                    clean_menu.append(food)
            
            result_meals[meal_type] = {
                "menu": clean_menu,
                "calories": row["CAL_INFO"]
            }
            
        return {
            "success": True,
            "school": "대평고등학교",
            "date": date,
            "meals": result_meals
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": "급식 데이터를 찾을 수 없습니다. 날짜를 확인해주세요.",
            "error": str(e)
        }


# ---------------------------------------------------------
# 4️⃣ 학교 찾기 API
# ---------------------------------------------------------
@app.get("/find_school")
def find_school(name: str):
    url = "https://open.neis.go.kr/hub/schoolInfo"
    params = {"Type": "json", "SCHUL_NM": name}
    try:
        response = requests.get(url, params=params).json()
        schools = response["schoolInfo"][1]["row"]
        return [{"학교이름": s["SCHUL_NM"], "교육청코드": s["ATPT_OFCDC_SC_CODE"], "학교코드": s["SD_SCHUL_CODE"]} for s in schools]
    except:
        return {"error": "학교를 찾을 수 없습니다."}


# ---------------------------------------------------------
# 5️⃣ 날씨 API
# ---------------------------------------------------------
@app.get("/weather")
def get_weather():
    url = "https://wttr.in/Suwon?format=j1"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        current = data["current_condition"][0]
        temp_c = current["temp_C"]
        weather_desc = current["lang_ko"][0]["value"] if "lang_ko" in current else current["weatherDesc"][0]["value"]
        humidity = current["humidity"]
        feels_like = current["FeelsLikeC"]
        
        advice = "오늘도 활기찬 학교 생활!"
        temp_int = int(temp_c)
        
        if "Rain" in current["weatherDesc"][0]["value"] or "Shower" in current["weatherDesc"][0]["value"]:
            advice = "비 소식이 있으니, 우산을 꼭 챙기세요. ☔"
        elif temp_int < 5:
            advice = "날씨가 아주 추우니, 따뜻하게 입고 가야 합니다. 🧣"
        elif temp_int > 28:
            advice = "날씨가 많이 덥습니다. 물을 자주 마셔주세요. ☀️"

        return {
            "success": True,
            "location": "Suwon",
            "current_temp": f"{temp_c}°C",
            "feels_like": f"{feels_like}°C",
            "condition": weather_desc,
            "humidity": f"{humidity}%",
            "doctor_advice": advice
        }

    except Exception as e:
        return {
            "success": False,
            "message": "날씨 정보를 가져오는 데 실패했습니다.",
            "error": str(e)
        }


# ---------------------------------------------------------
# 6️⃣ [참여형 기능] 급식 별점 시스템 (POST, GET)
# ---------------------------------------------------------
# 유니티에서 보낼 데이터의 형식을 정의
class Rating(BaseModel):
    date: str   # 예: "20260607"
    score: int  # 1 ~ 5 별점

@app.post("/meal/rating")
def add_meal_rating(rating: Rating):
    """유니티에서 별점을 서버로 보낼 때 사용하는 API"""
    if rating.date not in meal_ratings_db:
        meal_ratings_db[rating.date] = []
        
    meal_ratings_db[rating.date].append(rating.score)
    
    total_votes = len(meal_ratings_db[rating.date])
    avg_score = sum(meal_ratings_db[rating.date]) / total_votes
    
    return {
        "success": True,
        "message": "별점이 성공적으로 반영되었습니다!",
        "date": rating.date,
        "average_score": round(avg_score, 1),
        "total_votes": total_votes
    }

@app.get("/meal/rating")
def get_meal_rating(date: str):
    """유니티에서 특정 날짜의 평균 별점을 물어볼 때 사용하는 API"""
    if date in meal_ratings_db and len(meal_ratings_db[date]) > 0:
        avg_score = sum(meal_ratings_db[date]) / len(meal_ratings_db[date])
        return {
            "success": True,
            "date": date,
            "average_score": round(avg_score, 1),
            "total_votes": len(meal_ratings_db[date])
        }
    else:
        # 아직 투표가 없는 경우
        return {
            "success": True,
            "date": date, 
            "average_score": 0.0, 
            "total_votes": 0
        }

# SchoolApp_Real.py 에 추가할 코드

@app.get("/schedule")
def get_schedule(month: str = None):
    # month를 입력 안 하면 이번 달(예: "202606")을 기본값으로 사용
    if not month:
        month = datetime.now().strftime("%Y%m")
        
    url = "https://open.neis.go.kr/hub/SchoolSchedule"
    params = {
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": "J10",
        "SD_SCHUL_CODE": "7530554",
        "AA_FROM_YMD": f"{month}01", # 이번 달 1일부터
        "AA_TO_YMD": f"{month}31"    # 이번 달 31일까지
    }
    
    try:
        response = requests.get(url, params=params).json()
        events_row = response["SchoolSchedule"][1]["row"]
        
        # 날짜와 행사 이름만 예쁘게 뽑아서 리스트로 만들기
        schedule_list = []
        for row in events_row:
            # 행사가 있는 날만 추가 (토요휴업일 같은 건 제외하려면 여기서 필터링 가능)
            if row["EVENT_NM"]:
                schedule_list.append({
                    "date": row["AA_YMD"],
                    "event": row["EVENT_NM"]
                })
        
        return {"success": True, "month": month, "schedule": schedule_list}
    except:
        return {"success": False, "message": "이번 달 학사일정이 없거나 불러오지 못했습니다."}


# ---------------------------------------------------------
# 7️⃣ 시간표 조회 API (날짜 처리 기능 강화)
# ---------------------------------------------------------
@app.get("/timetable")
def get_timetable(grade: str, class_nm: str, date: str = None):
    """
    학년(grade)과 반(class_nm), 조회할 날짜(date)를 입력받아 시간표를 조회합니다.
    - date 예시: "2026-06-10", "2026/06/10", "20260610" 모두 가능
    - date를 입력하지 않으면 기본값으로 오늘 날짜를 조회합니다.
    """
    if not date:
        # 날짜를 입력하지 않았다면 오늘 날짜를 기본값으로 사용 (예: "20260610")
        date = datetime.now().strftime("%Y%m%d")
    else:
        # 프론트엔드에서 "2026-06-10"처럼 하이픈(-)이나 슬래시(/)를 넣어서 보내더라도
        # 숫자만 남기고 제거하여 나이스 규격("20260610")으로 맞춥니다.
        date = re.sub(r'[^0-9]', '', date)
        
    url = "https://open.neis.go.kr/hub/hisTimetable"
    params = {
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": "J10", # 경기도교육청
        "SD_SCHUL_CODE": "7530554",  # 대평고등학교
        "ALL_TI_YMD": date,          # 정제된 8자리 날짜 (YYYYMMDD)
        "GRADE": grade,
        "CLASS_NM": class_nm
    }
    
    try:
        response = requests.get(url, params=params).json()
        timetable_row = response["hisTimetable"][1]["row"]
        
        # 교시와 과목명 정보 추출
        timetable_list = []
        for row in timetable_row:
            timetable_list.append({
                "period": row["PERIO"],       # 교시 (1, 2, 3...)
                "subject": row["ITRT_CNTNT"]  # 과목명 (국어, 영어...)
            })
            
        # 교시 순서대로 정렬
        timetable_list.sort(key=lambda x: int(x["period"]))
        
        return {
            "success": True,
            "school": "대평고등학교",
            "date": date, # 가독성을 위해 프론트엔드에 다시 보낼 때도 전달
            "grade": grade,
            "class_nm": class_nm,
            "timetable": timetable_list
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"{date[:4]}년 {date[4:6]}월 {date[6:8]}일의 시간표 데이터를 찾을 수 없습니다. (주말, 공휴일, 방학 등)",
            "error": str(e)
        }


# ---------------------------------------------------------
# 8️⃣ 주요 행사 디데이(D-Day) 조회 API
# ---------------------------------------------------------
@app.get("/dday")
def get_dday():
    """
    현재 날짜를 기준으로 졸업식 및 주요 행사의 D-Day를 계산합니다.
    """
    today = datetime.now().date()
    
    try:
        # 1. 졸업식 D-Day 계산
        grad_date = datetime.strptime(GRADUATION_DATE, "%Y-%m-%d").date()
        grad_dday = (grad_date - today).days
        
        # 2. 2027학년도 수능일 D-Day 계산 (2026년 11월 12일 가정)
        csat_date = datetime.strptime("2026-11-12", "%Y-%m-%d").date()
        csat_dday = (csat_date - today).days
        
        # 유닛별 상태 텍스트 가공
        def format_dday(days):
            if days > 0:
                return f"D-{days}"
            elif days == 0:
                return "D-Day"
            else:
                return f"D+{abs(days)}"

        return {
            "success": True,
            "today": today.strftime("%Y-%m-%d"),
            "events": [
                {
                    "title": "대평고 졸업식 🎓",
                    "target_date": GRADUATION_DATE,
                    "days_left": grad_dday,
                    "dday_text": format_dday(grad_dday)
                },
                {
                    "title": "대학수학능력시험 📝",
                    "target_date": "2026-11-12",
                    "days_left": csat_dday,
                    "dday_text": format_dday(csat_dday)
                }
            ]
        }
    except Exception as e:
        return {
            "success": False,
            "message": "디데이 계산 중 에러가 발생했습니다.",
            "error": str(e)
        }
