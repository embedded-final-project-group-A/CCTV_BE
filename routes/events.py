from fastapi import APIRouter, Query
from typing import List
from datetime import datetime

router = APIRouter()

@router.get("/api/store/events", response_model=List[dict])
async def get_events_for_camera_fixed_video(store: str = Query(...), camera_label: str = Query(...)):
    """
    테스트 목적으로 모든 이벤트에 대해 고정된 비디오 URL을 반환합니다.
    """
    # 실제 데이터베이스를 조회하는 대신, 테스트를 위해 고정된 비디오 URL을 반환
    fixed_video_url = "http://localhost:8000/videos/store1_main.mp4"

    # 이벤트를 시뮬레이션하기 위한 더미 데이터
    # 실제 앱에서는 이 부분이 DB에서 데이터를 가져오는 코드가 됩니다.
    # 여기서는 단순히 몇 개의 더미 이벤트를 생성하여 반환합니다.
    # 날짜와 타입은 실제 프론트엔드에서 보여지는 내용을 모방합니다.
    events_data = [
        {
            "date": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d"),
            "type": "smoking",
            "videoUrl": fixed_video_url,
        },
        {
            "date": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
            "type": "theft",
            "videoUrl": fixed_video_url,
        },
        {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "type": "abandonment",
            "videoUrl": fixed_video_url,
        },
    ]
    # 필요하다면, 프론트엔드의 `CameraAccordion`에서 호출하는 방식에 맞춰
    # `camera_label`에 따라 다른 더미 데이터를 반환할 수도 있습니다.
    # 하지만 지금은 모든 카메라에 대해 동일하게 고정된 URL을 반환합니다.

    return events_data