# CCTV_BE

1. 가상환경
```
conda create -n "cctv"
conda activate cctv
pip install -r requirements.txt
```

2. DB 생성
- `test_db.py` 파일을 실행하여 데이터베이스 생성
- 테스트용 데이터가 필요 없다면 `insert_sample_data()`는 주석처리하여 실행

3. 실행
```
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

4. 테스트 코드 기준
- 현재 코드는 같은 프론트엔드와 백엔드 코드가 같은 localhost로 연결될 때 사용 가능한 코드입니다. 
- 백엔드에 저장되어 있는 폴더의 주소를 반환하여 영상을 재생합니다. 
- 만약 android studio 등 다른 주소를 사용해야한다면 예시 데이터베이스를 수정해야합니다. 