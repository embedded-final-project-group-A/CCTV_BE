# CCTV_BE

1. 가상환경
```
conda create -n "cctv"
conda activate cctv
pip install -r requirements.txt
``

2. 실행
```
uvicorn main:app --reload
```

3. 테스트 코드 기준
- 현재 코드는 프론트엔드 코드와 연동 테스트를 위한 테스트 코드입니다.
- youtube 링크를 보내면 프론트 엔드에서 동영상을 재생합니다.