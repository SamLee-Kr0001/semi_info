<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Semiconductor News Crawler</title>
    <style>
        /* 1. 상단 공백 최소화 및 폰트 사이즈 감소 */
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f4f6f9;
            margin: 0;            /* 페이지 전체 여백 제거 */
            padding: 10px;        /* 최소한의 내부 여백 */
            font-size: 13px;      /* 전체 폰트 사이즈 축소 */
            color: #333;
        }

        h1 {
            color: #0056b3;
            margin-top: 0;        /* 제목 위 공백 제거 */
            margin-bottom: 10px;
            font-size: 1.4rem;    /* 제목 크기 조정 */
            text-align: center;
        }

        .container {
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            padding: 15px;        /* 컨테이너 내부 여백 축소 */
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }

        /* 입력창 및 버튼 스타일 */
        .input-group {
            display: flex;
            gap: 5px;
            margin-bottom: 10px;
            justify-content: center;
        }

        input[type="text"] {
            padding: 5px 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            width: 250px;
            font-size: 13px;
        }

        button {
            padding: 5px 12px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            transition: background 0.3s;
        }

        .btn-add { background-color: #28a745; color: white; }
        .btn-crawl { background-color: #007bff; color: white; }
        .btn-add:hover { background-color: #218838; }
        .btn-crawl:hover { background-color: #0069d9; }

        /* 키워드 태그 스타일 */
        .keyword-container {
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
            margin-bottom: 15px;
            justify-content: center;
        }

        .keyword-tag {
            background-color: #e9ecef;
            color: #495057;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 12px;
            display: flex;
            align-items: center;
            border: 1px solid #ced4da;
        }

        .keyword-tag span {
            margin-left: 6px;
            cursor: pointer;
            color: #dc3545;
            font-weight: bold;
        }

        /* 결과 테이블 스타일 (간격 축소) */
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
            font-size: 12px; /* 테이블 폰트 더 축소 */
        }
        th, td {
            padding: 6px 8px; /* 셀 간격 축소 */
            border: 1px solid #ddd;
            text-align: left;
        }
        th { background-color: #f8f9fa; }
        
        /* 2. 하단 서명 (Made by LSH) */
        .footer-signature {
            position: fixed;   /* 화면에 고정 */
            bottom: 5px;       /* 하단에서 5px 위 */
            left: 5px;         /* 좌측에서 5px 오른쪽 */
            font-size: 8px;    /* 요청하신 폰트 사이즈 8 */
            color: #888;
            font-style: italic;
            z-index: 100;      /* 다른 요소 위에 표시 */
        }
    </style>
</head>
<body>

    <div class="container">
        <h1>Semiconductor News Crawler</h1>

        <div class="input-group">
            <input type="text" id="keywordInput" placeholder="키워드 입력 (예: HBM, Photoresist)">
            <button class="btn-add" onclick="addKeyword()">키워드 추가</button>
            <button class="btn-crawl" onclick="startCrawl()">뉴스 검색 시작</button>
        </div>

        <div class="keyword-container" id="keywordList"></div>

        <div id="resultArea">
            </div>
    </div>

    <div class="footer-signature">Made by LSH</div>

    <script>
        // 페이지 로드 시 저장된 키워드 불러오기
        document.addEventListener('DOMContentLoaded', () => {
            loadKeywords();
            
            // 엔터키 입력 시 키워드 추가 기능
            document.getElementById("keywordInput").addEventListener("keypress", function(event) {
                if (event.key === "Enter") {
                    addKeyword();
                }
            });
        });

        // 키워드 추가 함수
        function addKeyword() {
            const input = document.getElementById('keywordInput');
            const keyword = input.value.trim();

            if (keyword) {
                // 이미 있는 키워드인지 확인
                const currentKeywords = getKeywordsFromStorage();
                if (!currentKeywords.includes(keyword)) {
                    createKeywordElement(keyword);
                    saveKeywordToStorage(keyword);
                } else {
                    alert('이미 등록된 키워드입니다.');
                }
                input.value = ''; // 입력창 초기화
            }
        }

        // 화면에 키워드 태그 생성
        function createKeywordElement(text) {
            const list = document.getElementById('keywordList');
            const div = document.createElement('div');
            div.className = 'keyword-tag';
            // 텍스트와 삭제 버튼(X) 구성
            div.innerHTML = `${text} <span onclick="removeKeyword(this, '${text}')">×</span>`;
            list.appendChild(div);
        }

        // 키워드 삭제 함수
        function removeKeyword(element, text) {
            // 화면에서 제거
            element.parentElement.remove();
            // 저장소에서 제거
            removeKeywordFromStorage(text);
        }

        // --- LocalStorage 관리 (저장/불러오기) ---

        function getKeywordsFromStorage() {
            const stored = localStorage.getItem('myKeywords');
            return stored ? JSON.parse(stored) : [];
        }

        function saveKeywordToStorage(keyword) {
            const keywords = getKeywordsFromStorage();
            keywords.push(keyword);
            localStorage.setItem('myKeywords', JSON.stringify(keywords));
        }

        function removeKeywordFromStorage(keywordToDelete) {
            let keywords = getKeywordsFromStorage();
            keywords = keywords.filter(k => k !== keywordToDelete);
            localStorage.setItem('myKeywords', JSON.stringify(keywords));
        }

        function loadKeywords() {
            const keywords = getKeywordsFromStorage();
            keywords.forEach(keyword => {
                createKeywordElement(keyword);
            });
        }

        // --- 크롤링 요청 (Python 연동) ---
        async function startCrawl() {
            const keywords = getKeywordsFromStorage();
            
            if (keywords.length === 0) {
                alert("키워드를 하나 이상 추가해주세요.");
                return;
            }

            const resultArea = document.getElementById('resultArea');
            resultArea.innerHTML = '<p style="text-align:center;">🔍 뉴스를 검색 중입니다...</p>';

            try {
                // app.py의 /crawl 엔드포인트로 키워드 전송
                const response = await fetch('/crawl', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ keywords: keywords }),
                });

                const data = await response.json();
                
                // 결과 테이블 렌더링 (예시)
                let html = '<table><thead><tr><th>Source</th><th>Title</th><th>Link</th></tr></thead><tbody>';
                
                // 데이터가 비어있을 경우 처리
                if (!data.results || data.results.length === 0) {
                     resultArea.innerHTML = '<p style="text-align:center;">검색 결과가 없습니다.</p>';
                     return;
                }

                data.results.forEach(item => {
                    html += `<tr>
                        <td>${item.source}</td>
                        <td>${item.title}</td>
                        <td><a href="${item.link}" target="_blank">Link</a></td>
                    </tr>`;
                });
                html += '</tbody></table>';
                resultArea.innerHTML = html;

            } catch (error) {
                console.error('Error:', error);
                resultArea.innerHTML = '<p style="text-align:center; color:red;">오류가 발생했습니다.</p>';
            }
        }
    </script>
</body>
</html>
