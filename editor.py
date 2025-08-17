# app.py
import streamlit as st
from typing import List, Dict, Any

st.set_page_config(layout="wide", page_title="재귀형 블록 기반 편집기")

# --------------------------------------------
# 유틸
# --------------------------------------------
def make_block(name: str) -> Dict[str, Any]:
    return {"type": "block", "name": name, "components": []}

def ensure_initial_state():
    if "blocks" not in st.session_state or not isinstance(st.session_state.blocks, list):
        st.session_state.blocks = [make_block("블록1")]
    elif len(st.session_state.blocks) == 0:
        st.session_state.blocks.append(make_block("블록1"))

ensure_initial_state()

def _get_parent_list_and_index(path: List[int]):
    if len(path) == 1:
        return st.session_state.blocks, path[0]
    cur = st.session_state.blocks[path[0]]
    for k in path[1:-1]:
        cur = cur["components"][k]
    return cur["components"], path[-1]

def _get_block_by_path(path: List[int]) -> Dict[str, Any]:
    if len(path) == 1:
        return st.session_state.blocks[path[0]]
    cur = st.session_state.blocks[path[0]]
    for k in path[1:]:
        cur = cur["components"][k]
    return cur

# --------------------------------------------
# 콜백
# --------------------------------------------
def add_top_block():
    st.session_state.blocks.append(make_block(f"블록{len(st.session_state.blocks)+1}"))

def delete_block_by_path(path: List[int]):
    parent_list, idx = _get_parent_list_and_index(path)
    if parent_list is st.session_state.blocks and len(parent_list) <= 1:
        return  # 최상위는 최소 1개 유지
    parent_list.pop(idx)

def move_block_up_by_path(path: List[int]):
    parent_list, idx = _get_parent_list_and_index(path)
    if idx > 0:
        parent_list[idx-1], parent_list[idx] = parent_list[idx], parent_list[idx-1]

def move_block_down_by_path(path: List[int]):
    parent_list, idx = _get_parent_list_and_index(path)
    if idx < len(parent_list) - 1:
        parent_list[idx+1], parent_list[idx] = parent_list[idx], parent_list[idx+1]

def add_component_to_block(path: List[int]):
    blk = _get_block_by_path(path)
    blk["components"].append({
        "type": "select",
        "data": {"choice": "텍스트"}
    })

def set_component_type(path: List[int], comp_idx: int, choice: str):
    blk = _get_block_by_path(path)
    if choice == "텍스트":
        blk["components"][comp_idx] = {
            "type": "text",
            "data": {"content": "여기에 텍스트를 입력하세요..."},
        }
    elif choice == "내부 블록":
        blk["components"][comp_idx] = make_block("내부 블록")
    else:
        blk["components"][comp_idx] = {
            "type": "select",
            "data": {"choice": "텍스트"},
        }

# --------------------------------------------
# 미리보기 Markdown 빌더
# --------------------------------------------
def build_markdown_from_blocks(blocks: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for idx, blk in enumerate(blocks):
        lines.extend(_block_to_md_lines(blk, depth=1))
        if idx < len(blocks) - 1:
            lines.append("")  # 블록 사이 빈 줄
    return "\n".join(lines)

def _block_to_md_lines(block: Dict[str, Any], depth: int) -> List[str]:
    lines: List[str] = []
    # 헤딩 레벨(최대 h6로 캡)
    level = min(max(depth, 1), 6)
    heading_prefix = "#" * level

    # 블록 제목
    block_name = block.get("name", "블록")
    lines.append(f"{heading_prefix} {block_name}")

    # 컴포넌트 처리
    for comp in block.get("components", []):
        ctype = comp.get("type")
        if ctype == "text":
            content = (comp.get("data") or {}).get("content", "").strip()
            if content:
                for line in content.splitlines():
                    line = line.strip()
                    if line:
                        lines.append(f"* {line}")
            else:
                lines.append("* ")
        elif ctype == "block":
            # 내부 블록 재귀
            lines.append("")  # 상위 컴포넌트와 구분
            lines.extend(_block_to_md_lines(comp, depth=depth+1))
        # select(자리표시자)는 미리보기에서 표시하지 않음
    return lines

# --------------------------------------------
# 렌더링
# --------------------------------------------
def render_block(path: List[int]):
    blk = _get_block_by_path(path)

    with st.container(border=True):
        # 상단 행: 라벨/이동/삭제
        cols_top = st.columns([1, 1, 6, 1, 1])
        with cols_top[0]:
            st.markdown(f"**블록 #{' / '.join(str(x+1) for x in path)}**")
        with cols_top[1]:
            st.button("▲ 위로", key=f"up_{'_'.join(map(str,path))}",
                      on_click=move_block_up_by_path, args=(path,),
                      disabled=_is_first_in_parent(path))
        with cols_top[3]:
            st.button("▼ 아래로", key=f"down_{'_'.join(map(str,path))}",
                      on_click=move_block_down_by_path, args=(path,),
                      disabled=_is_last_in_parent(path))
        with cols_top[4]:
            st.button("🗑️ 삭제", key=f"del_{'_'.join(map(str,path))}",
                      on_click=delete_block_by_path, args=(path,),
                      disabled=_is_top_level_and_single(path))

        # 블록 이름(입력 가능) — 미리보기에서는 깊이에 따라 #, ## … 처리됨
        new_name = st.text_input(
            "블록 이름",
            value=blk.get("name", f"블록{' / '.join(str(x+1) for x in path)}"),
            key=f"blkname_{'_'.join(map(str,path))}"
        )
        blk["name"] = new_name

        # 컴포넌트 추가
        st.button("➕ 컴포넌트 추가",
                  key=f"addcomp_{'_'.join(map(str,path))}",
                  on_click=add_component_to_block, args=(path,))

        st.markdown("---")

        # 컴포넌트 렌더링 (컴포넌트 이름 입력칸은 제거됨)
        for j, comp in enumerate(list(blk["components"])):
            ctype = comp.get("type")
            comp_key_prefix = f"{'_'.join(map(str,path))}_{j}"

            if ctype == "select":
                col_sel, col_apply = st.columns([5, 1])
                with col_sel:
                    choice = st.selectbox(
                        "컴포넌트 타입 선택",
                        options=["텍스트", "내부 블록"],
                        index=["텍스트", "내부 블록"].index(comp.get("data", {}).get("choice", "텍스트"))
                              if comp.get("data") else 0,
                        key=f"select_{comp_key_prefix}",
                    )
                with col_apply:
                    if st.button("적용", key=f"apply_{comp_key_prefix}"):
                        set_component_type(path, j, choice)
                st.caption("타입을 선택하고 ‘적용’을 누르면 해당 타입으로 전환됩니다.")

            elif ctype == "text":
                new_val = st.text_area(
                    "텍스트 내용",
                    value=comp["data"].get("content", ""),
                    key=f"text_{comp_key_prefix}",
                    height=100,
                )
                comp["data"]["content"] = new_val

            elif ctype == "block":
                render_block(path + [j])

            st.markdown("")  # 컴포넌트 간 여백

def _is_top_level_and_single(path: List[int]) -> bool:
    return len(path) == 1 and len(st.session_state.blocks) == 1

def _is_first_in_parent(path: List[int]) -> bool:
    parent_list, idx = _get_parent_list_and_index(path)
    return idx == 0

def _is_last_in_parent(path: List[int]) -> bool:
    parent_list, idx = _get_parent_list_and_index(path)
    return idx == len(parent_list) - 1

# --------------------------------------------
# 화면 루트
# --------------------------------------------
st.markdown("### 에디터 영역")

# 최상위 블록들 렌더링
for i in range(len(st.session_state.blocks)):
    render_block([i])
    st.markdown("")

# 하단 전용: 최상위 블록 추가
st.button("새 블록 추가", on_click=add_top_block, key="add_block_bottom")

st.divider()
st.subheader("미리보기 (Markdown)")
md_preview = build_markdown_from_blocks(st.session_state.blocks)
st.code(md_preview, language="markdown")
