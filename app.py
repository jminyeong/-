import streamlit as st
import json
import os
from anthropic import Anthropic

# ── 페이지 설정 ──────────────────────────────────────────────
st.set_page_config(page_title="점심 뭐 먹지?", page_icon="🍱", layout="centered")

st.title("🍱 점심 뭐 먹지?")
st.caption("오늘 날씨, 기분, 먹고 싶은 거 말하면 딱 맞는 가게랑 메뉴 추천해드려요!")

# ── Anthropic 클라이언트 ──────────────────────────────────────
api_key = st.secrets.get("ANTHROPIC_API_KEY", os.environ.get("ANTHROPIC_API_KEY", ""))
if not api_key:
    st.error("⚠️ ANTHROPIC_API_KEY가 설정되지 않았어요. Streamlit Secrets에 추가해주세요.")
    st.stop()

client = Anthropic(api_key=api_key)

# ── 샘플 가게 데이터 ──────────────────────────────────────────
if "stores" not in st.session_state:
    st.session_state.stores = [
        {
            "name": "을지면옥",
            "location": "을지로 3가",
            "price": "12,000원",
            "category": "한식",
            "busy": "붐빔",
            "menus": "평양냉면, 비빔냉면, 수육",
            "note": "냉면 맛집, 줄 김",
        },
        {
            "name": "이태원 부대찌개",
            "location": "강남역 근처",
            "price": "9,000원",
            "category": "한식",
            "busy": "보통",
            "menus": "부대찌개, 김치찌개, 된장찌개",
            "note": "얼큰하고 든든함, 공기밥 무한리필",
        },
        {
            "name": "스시야",
            "location": "선릉역 5번출구",
            "price": "15,000원",
            "category": "일식",
            "busy": "한산",
            "menus": "점심 스시세트, 연어덮밥, 우동",
            "note": "점심 스시세트 있음, 조용한 편",
        },
        {
            "name": "감성타코",
            "location": "성수동",
            "price": "11,000원",
            "category": "양식",
            "busy": "보통",
            "menus": "타코 3개 세트, 부리또, 퀘사디아",
            "note": "타코 3개 세트 추천, 소스 다양",
        },
        {
            "name": "마라탕후루",
            "location": "홍대입구역",
            "price": "13,000원",
            "category": "중식",
            "busy": "붐빔",
            "menus": "마라탕, 마라샹궈, 훠궈",
            "note": "매운맛 조절 가능, 재료 선택 가능",
        },
    ]

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


# ── 시스템 프롬프트 생성 ──────────────────────────────────────
def build_system_prompt():
    if not st.session_state.stores:
        return "등록된 가게가 없다고 안내하고, 가게를 먼저 추가하라고 알려주세요."

    store_lines = []
    for s in st.session_state.stores:
        line = (
            f"- 가게명: {s['name']} | 종류: {s['category']} | 위치: {s['location']} | "
            f"가격: {s['price']} | 혼잡도: {s['busy']} | 메뉴: {s['menus']}"
        )
        if s.get("note"):
            line += f" | 특징: {s['note']}"
        store_lines.append(line)

    store_context = "\n".join(store_lines)

    return f"""당신은 친근한 점심 추천 챗봇이에요. 사용자가 등록해둔 가게 목록에서만 추천해야 해요.

[내 가게 목록]
{store_context}

[추천 방식]
1. 사용자의 날씨, 기분, 컨디션, 인원 등을 파악해서 딱 맞는 가게 1~2곳을 추천하세요.
2. 가게 추천 시 반드시 구체적인 메뉴도 같이 추천하세요. 예) "부대찌개집 가서 부대찌개에 공기밥 추가하면 딱이에요!"
3. 친근하고 자연스러운 말투로, 마치 맛집 잘 아는 친구가 추천해주듯이 말하세요.
4. 혼잡도도 고려해주세요. 바쁜 사람이면 한산한 곳, 시간 여유 있으면 맛집 추천.
5. 추천 후 자연스럽게 후속 질문도 해주세요.
6. 등록된 가게 목록에 없는 곳은 절대 추천하지 마세요.

[말투 예시]
- "오 비 오는 날엔 역시 얼큰한 게 최고죠!"
- "그럼 부대찌개 어때요? 얼큰하고 든든해서 딱일 것 같은데!"
- "혼잡도가 보통이라 줄 안 서도 될 것 같아요!"
"""


# ── 탭 구성 ──────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["💬 추천 받기", "📋 가게 목록", "➕ 가게 추가"])

# ────────────────────────────────────────────────────────────
# TAB 1 — 챗봇 추천
# ────────────────────────────────────────────────────────────
with tab1:

    # 빠른 입력 버튼
    st.write("**오늘 상황을 골라보세요**")
    col1, col2, col3, col4 = st.columns(4)
    quick_inputs = {
        "🌧️ 비+얼큰": "오늘 비 오는데 얼큰한 거 땡겨",
        "🥢 가볍게 혼밥": "혼자 가볍게 먹고 싶어",
        "⚡ 빨리 먹기": "시간 없어서 빨리 먹어야 해",
        "👥 팀이랑": "팀원 3명이랑 같이 갈 곳 추천해줘",
    }
    for col, (label, prompt) in zip([col1, col2, col3, col4], quick_inputs.items()):
        if col.button(label, use_container_width=True):
            st.session_state["quick_input"] = prompt

    st.divider()

    # 대화 출력
    if not st.session_state.chat_history:
        with st.chat_message("assistant"):
            st.markdown(
                "안녕하세요! 🍱 오늘 점심 뭐 드실지 골라드릴게요.\n\n"
                "날씨, 기분, 인원 수 등 자유롭게 말씀해주세요!"
            )

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 입력 처리
    quick_val = st.session_state.pop("quick_input", None)
    user_input = st.chat_input("예) 오늘 비 오고 얼큰한 거 땡겨요...")
    final_input = quick_val or user_input

    if final_input:
        with st.chat_message("user"):
            st.markdown(final_input)
        st.session_state.chat_history.append({"role": "user", "content": final_input})

        with st.chat_message("assistant"):
            with st.spinner("추천 중..."):
                messages = [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.chat_history
                ]
                response = client.messages.create(
                    model="claude-opus-4-5",
                    max_tokens=1000,
                    system=build_system_prompt(),
                    messages=messages,
                )
                reply = response.content[0].text
                st.markdown(reply)

        st.session_state.chat_history.append({"role": "assistant", "content": reply})

    if st.session_state.chat_history:
        if st.button("🔄 대화 초기화", type="secondary"):
            st.session_state.chat_history = []
            st.rerun()

# ────────────────────────────────────────────────────────────
# TAB 2 — 가게 목록
# ────────────────────────────────────────────────────────────
with tab2:
    st.subheader("📋 내 가게 목록")

    if not st.session_state.stores:
        st.info("아직 등록된 가게가 없어요. '가게 추가' 탭에서 추가해보세요!")
    else:
        categories = ["전체"] + sorted(set(s["category"] for s in st.session_state.stores))
        selected_cat = st.selectbox("카테고리 필터", categories)

        filtered = (
            st.session_state.stores
            if selected_cat == "전체"
            else [s for s in st.session_state.stores if s["category"] == selected_cat]
        )

        for store in filtered:
            busy_icon = {"붐빔": "🔴", "보통": "🟡", "한산": "🟢"}.get(store["busy"], "⚪")
            with st.container(border=True):
                col1, col2 = st.columns([5, 1])
                with col1:
                    st.markdown(f"**{store['name']}** &nbsp; `{store['category']}`")
                    st.caption(
                        f"📍 {store['location']}  ·  💰 {store['price']}  ·  {busy_icon} {store['busy']}"
                    )
                    if store.get("menus"):
                        st.markdown(f"🍽️ **메뉴:** {store['menus']}")
                    if store.get("note"):
                        st.caption(f"📝 {store['note']}")
                with col2:
                    real_idx = st.session_state.stores.index(store)
                    if st.button("삭제", key=f"del_{real_idx}", type="secondary"):
                        st.session_state.stores.pop(real_idx)
                        st.rerun()

        st.divider()
        st.caption(f"총 {len(st.session_state.stores)}개 가게 등록됨")

        json_str = json.dumps(st.session_state.stores, ensure_ascii=False, indent=2)
        st.download_button(
            label="📥 가게 목록 내보내기 (JSON)",
            data=json_str,
            file_name="my_stores.json",
            mime="application/json",
        )

# ────────────────────────────────────────────────────────────
# TAB 3 — 가게 추가
# ────────────────────────────────────────────────────────────
with tab3:
    st.subheader("➕ 새 가게 추가")

    with st.form("add_store_form", clear_on_submit=True):
        name = st.text_input("가게 이름 *", placeholder="예) 을지면옥")

        col1, col2 = st.columns(2)
        with col1:
            location = st.text_input("위치", placeholder="예) 강남역 3번출구")
            category = st.selectbox(
                "음식 종류",
                ["한식", "중식", "일식", "양식", "분식", "패스트푸드", "카페/샌드위치", "기타"],
            )
        with col2:
            price = st.text_input("가격대 (1인분)", placeholder="예) 9,000원")
            busy = st.selectbox("혼잡도", ["보통", "붐빔", "한산"])

        menus = st.text_input(
            "대표 메뉴 *",
            placeholder="예) 부대찌개, 김치찌개, 된장찌개",
        )
        st.caption("AI가 메뉴까지 추천해주려면 꼭 입력해주세요!")

        note = st.text_input("메모", placeholder="예) 공기밥 무한리필, 주차 가능")

        submitted = st.form_submit_button("➕ 추가하기", type="primary", use_container_width=True)
        if submitted:
            if not name.strip():
                st.error("가게 이름을 입력해주세요!")
            elif not menus.strip():
                st.error("대표 메뉴를 입력해주세요!")
            else:
                st.session_state.stores.append(
                    {
                        "name": name.strip(),
                        "location": location.strip() or "위치 미입력",
                        "price": price.strip() or "가격 미입력",
                        "category": category,
                        "busy": busy,
                        "menus": menus.strip(),
                        "note": note.strip(),
                    }
                )
                st.success(f"✅ '{name}' 추가됐어요!")
                st.balloons()
