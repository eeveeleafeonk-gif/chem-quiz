import streamlit as st
import random
import pandas as pd
from rdkit import Chem
from rdkit.Chem import Draw
import base64
from io import BytesIO

# --- 1. ファイル切り替え対応のデータ読み込み ---
@st.cache_data
def load_data(filename):
    try:
        df = pd.read_excel(filename)
        df = df.dropna(subset=["structure", "abbr", "name"])
        df["structure"] = df["structure"].astype(str).str.strip()
        df["abbr"] = df["abbr"].astype(str).str.strip()
        df["name"] = df["name"].astype(str).str.strip()
        return df.to_dict(orient="records")
    except FileNotFoundError:
        return []

# --- 2. RDKit画像生成 ---
def get_structure_image(smiles):
    mol = Chem.MolFromSmiles(smiles)
    return Draw.MolToImage(mol, size=(400, 400)) if mol else None

def get_image_base64(smiles):
    mol = Chem.MolFromSmiles(smiles)
    if mol:
        img = Draw.MolToImage(mol, size=(150, 150))
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        return f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode()}"
    return None

# --- 3. 画面レイアウト・サイドバー ---
st.title("🧪 有機化学 構造クイズ")

st.sidebar.subheader("📂 データセット選択")
dataset_choice = st.sidebar.selectbox("クイズのテーマを選んでください", ["略語編", "慣用名・複素環編"])

# 選択されたデータセットに応じて読み込むファイルを変更
file_map = {
    "略語編": "compounds_abbr.xlsx",
    "慣用名・複素環編": "compounds_trivial.xlsx"
}
selected_file = file_map[dataset_choice]
compounds = load_data(selected_file)

# データセットが切り替わったらクイズ状態をリセットする
if 'current_dataset' not in st.session_state:
    st.session_state.current_dataset = dataset_choice

if st.session_state.current_dataset != dataset_choice:
    st.session_state.current_dataset = dataset_choice
    st.session_state.current_q = None
    st.session_state.test_active = False

st.sidebar.divider()
mode = st.sidebar.radio("モード選択", [
    "📝 エンドレス練習 (4択)", 
    "✍️ エンドレス練習 (書き取り)", 
    "💯 実力テスト (スコア測定)", 
    "📚 一覧（まとめ表示）"
])

# データ不足時のエラーハンドリング
if len(compounds) < 4:
    st.error(f"【エラー】 `{selected_file}` に化合物を4つ以上登録するか、ファイルを作成してアップロードしてください。（現在: {len(compounds)}個）")
    st.stop()

# --- 4. セッション管理 ---
if 'current_q' not in st.session_state: st.session_state.current_q = None
if 'test_active' not in st.session_state: st.session_state.test_active = False
if 'test_q_list' not in st.session_state: st.session_state.test_q_list = []
if 'test_index' not in st.session_state: st.session_state.test_index = 0
if 'test_score' not in st.session_state: st.session_state.test_score = 0
if 'test_mistakes' not in st.session_state: st.session_state.test_mistakes = []
if 'answered' not in st.session_state: st.session_state.answered = False

def generate_options(target):
    wrong_compounds = random.sample([c for c in compounds if c != target], 3)
    opts = [target] + wrong_compounds
    abbr_opts = [opt["abbr"] for opt in opts]
    name_opts = [opt["name"] for opt in opts]
    random.shuffle(abbr_opts)
    random.shuffle(name_opts)
    st.session_state.abbr_options = abbr_opts
    st.session_state.name_options = name_opts

def next_practice_question():
    st.session_state.current_q = random.choice(compounds)
    generate_options(st.session_state.current_q)
    st.session_state.answered = False

if st.session_state.current_q is None:
    next_practice_question()

# 見出しの動的変更
col1_name = "略語" if dataset_choice == "略語編" else "慣用名"
col2_name = "正式名称" if dataset_choice == "略語編" else "系統名/別名"

# --- 5. 各モードのロジック ---
if mode == "📚 一覧（まとめ表示）":
    st.subheader(f"📚 {dataset_choice} 一覧")
    df_display = pd.DataFrame(compounds)
    df_display["構造画像"] = df_display["structure"].apply(get_image_base64)
    df_display = df_display[["構造画像", "abbr", "name", "structure"]].rename(
        columns={"structure": "SMILES", "abbr": col1_name, "name": col2_name}
    )
    st.dataframe(
        df_display,
        column_config={"構造画像": st.column_config.ImageColumn("構造"), "SMILES": st.column_config.TextColumn(disabled=True)},
        use_container_width=True, hide_index=True
    )

elif mode == "💯 実力テスト (スコア測定)":
    if not st.session_state.test_active:
        st.subheader("💯 実力テストの設定")
        test_type = st.radio("クイズ形式", ["4択クイズ", "書き取りクイズ"])
        max_q = min(len(compounds), 50)
        q_count = st.number_input("問題数", min_value=1, max_value=max_q, value=min(10, max_q))
        
        if st.button("🚀 テスト開始！", type="primary"):
            st.session_state.test_active = True
            st.session_state.test_type = test_type
            st.session_state.test_q_list = random.sample(compounds, q_count)
            st.session_state.test_index = 0
            st.session_state.test_score = 0
            st.session_state.test_mistakes = []
            st.session_state.answered = False
            st.session_state.current_q = st.session_state.test_q_list[0]
            generate_options(st.session_state.current_q)
            st.rerun()
            
    else:
        total_q = len(st.session_state.test_q_list)
        current_idx = st.session_state.test_index
        target = st.session_state.test_q_list[current_idx]
        
        st.progress((current_idx) / total_q)
        st.write(f"**第 {current_idx + 1} 問 / 全 {total_q} 問**")
        
        img = get_structure_image(target['structure'])
        if img:
            st.image(img, use_container_width=False)
        else:
            st.error(f"⚠️ 構造式の描画エラー\n\n【{col1_name}】{target['abbr']} 【SMILES】{target['structure']}")
            
        st.divider()

        with st.form("test_form"):
            if st.session_state.test_type == "4択クイズ":
                user_abbr = st.radio(f"① {col1_name}はどれ？", st.session_state.abbr_options, index=None, disabled=st.session_state.answered)
                user_name = st.radio(f"② {col2_name}はどれ？", st.session_state.name_options, index=None, disabled=st.session_state.answered)
            else:
                user_abbr = st.text_input(f"{col1_name}を入力", disabled=st.session_state.answered)
                user_name = st.text_input(f"{col2_name}を入力", disabled=st.session_state.answered)
                
            submitted = st.form_submit_button("解答する", disabled=st.session_state.answered)
            
            if submitted:
                if st.session_state.test_type == "4択クイズ" and (user_abbr is None or user_name is None):
                    st.warning(f"{col1_name}と{col2_name}の両方を選択してください！")
                else:
                    st.session_state.answered = True
                    is_abbr_ok = (user_abbr.strip().lower() == target["abbr"].lower()) if user_abbr else False
                    is_name_ok = (user_name.strip().lower() == target["name"].lower()) if user_name else False
                    
                    if is_abbr_ok and is_name_ok:
                        st.success("⭕ 正解！")
                        st.session_state.test_score += 1
                    else:
                        st.error(f"❌ 不正解... 【正解】 {col1_name}: {target['abbr']} / {col2_name}: {target['name']}")
                        st.session_state.test_mistakes.append(target)
                    st.rerun()
        
        if st.session_state.answered:
            if current_idx + 1 < total_q:
                if st.button("⏭️ 次の問題へ", type="primary"):
                    st.session_state.test_index += 1
                    st.session_state.current_q = st.session_state.test_q_list[st.session_state.test_index]
                    generate_options(st.session_state.current_q)
                    st.session_state.answered = False
                    st.rerun()
            else:
                if st.button("🏆 結果を見る", type="primary"):
                    st.session_state.test_active = False
                    st.session_state.show_result = True
                    st.rerun()

    if not st.session_state.test_active and getattr(st.session_state, 'show_result', False):
        st.subheader("🎉 テスト結果")
        total_q = len(st.session_state.test_q_list)
        score = st.session_state.test_score
        rate = (score / total_q) * 100
        
        st.metric(label="正解率", value=f"{score} / {total_q} 問", delta=f"{rate:.1f}%")
        
        if rate == 100:
            st.balloons()
            st.success("完璧です！全問正解おめでとうございます！")
        elif len(st.session_state.test_mistakes) > 0:
            st.warning("復習が必要な化合物があります。")
            st.write("### ❌ 間違えた化合物リスト")
            mistake_df = pd.DataFrame(st.session_state.test_mistakes)
            mistake_df = mistake_df[["abbr", "name", "structure"]].rename(columns={"abbr": col1_name, "name": col2_name, "structure": "SMILES"})
            st.dataframe(mistake_df, hide_index=True)
            
        if st.button("もう一度テストをする"):
            st.session_state.show_result = False
            st.rerun()

else:
    if st.sidebar.button("⏭️ 次の問題へスキップ"):
        next_practice_question()
        st.rerun()

    target = st.session_state.current_q
    st.subheader(f"【練習問題】この化合物の{col1_name}と{col2_name}は？")
    img = get_structure_image(target['structure'])
    
    if img:
        st.image(img, use_container_width=False)
    else:
        st.error(f"⚠️ 構造式の描画エラー\n\n【{col1_name}】{target['abbr']} 【SMILES】{target['structure']}")
        
    st.divider()

    with st.form("practice_form"):
        if "4択" in mode:
            user_abbr = st.radio(f"① {col1_name}はどれ？", st.session_state.abbr_options, index=None, disabled=st.session_state.answered)
            user_name = st.radio(f"② {col2_name}はどれ？", st.session_state.name_options, index=None, disabled=st.session_state.answered)
        else:
            user_abbr = st.text_input(f"{col1_name}を入力", disabled=st.session_state.answered)
            user_name = st.text_input(f"{col2_name}を入力", disabled=st.session_state.answered)
            
        submitted = st.form_submit_button("解答する", disabled=st.session_state.answered)
        
        if submitted:
            st.session_state.answered = True
            if "4択" in mode:
                is_abbr_ok = (user_abbr == target["abbr"])
                is_name_ok = (user_name == target["name"])
            else:
                is_abbr_ok = (user_abbr.strip().lower() == target["abbr"].lower())
                is_name_ok = (user_name.strip().lower() == target["name"].lower())
            
            if is_abbr_ok and is_name_ok:
                st.success("⭕ 正解です！サイドバーからスキップするか、下のボタンを押してください。")
            else:
                st.error(f"❌ 不正解... 【正解】 {col1_name}: {target['abbr']} / {col2_name}: {target['name']}")
    
    if st.session_state.answered:
        if st.button("⏭️ 次の問題へ", type="primary"):
            next_practice_question()
            st.rerun()