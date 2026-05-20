import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import re
from collections import Counter
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# KONFIGURASI
st.set_page_config(
    page_title="SkillBridge AI Dashboard",
    layout="wide",
)
st_autorefresh(interval=60000, key="dashboard_refresh")
sns.set_theme(style="whitegrid", palette="muted")

# LOAD DATA
@st.cache_data(ttl=60)
def load_data():
    df_skkni  = pd.read_csv("5_data_pekerjaan.csv")
    df_github = pd.read_csv("cleaned_job_5.csv")

    # Jumlah unit kompetensi unik per jabatan
    unit_per_job = (
        df_skkni.groupby("Jabatan")["Judul Unit"]
        .nunique()
        .reset_index(name="Total Unit")
        .sort_values("Total Unit", ascending=False)
    )

    # Skill paling sering diminta industri (kolom requirement)
    def extract_skills(text):
        if pd.isna(text):
            return []
        parts = re.split(r"[,;\n]", str(text))
        return [p.strip().title() for p in parts if 2 < len(p.strip()) < 60]

    all_skills = [
        skill
        for text in df_github["requirement"]
        for skill in extract_skills(text)
    ]
    skill_counter = Counter(all_skills)
    df_skill_github = pd.DataFrame(
        skill_counter.most_common(30),
        columns=["Skill", "Frekuensi"]
    )

    # Gap analysis SKKNI vs GitHub 
    skill_github_set = set([s for s, _ in skill_counter.most_common(80)])
    stop_words = {"dan", "atau", "yang", "untuk", "dengan", "dalam",
                  "pada", "ke", "di", "dari", "secara", "sesuai"}

    def match_score(skkni_skill, github_skills):
        words = set(skkni_skill.lower().split()) - stop_words
        return sum(1 for gs in github_skills
                   if len(words & set(gs.lower().split())) > 0)

    gap_rows = []
    for job in df_skkni["Jabatan"].dropna().unique():
        skills = (
            df_skkni[df_skkni["Jabatan"] == job]["Judul Unit"]
            .dropna().str.strip().str.title().unique()
        )
        for skill in skills:
            score = match_score(skill, skill_github_set)
            gap_rows.append({
                "Jabatan":     job,
                "Skill SKKNI": skill[:50] + ("..." if len(skill) > 50 else ""),
                "Match Score": score,
                "Status":      "Relevan" if score > 0 else "Gap (tidak ditemukan)"
            })

    df_gap = pd.DataFrame(gap_rows)

    return df_skkni, df_github, unit_per_job, df_skill_github, df_gap

# LOAD
try:
    df_skkni, df_github, unit_per_job, df_skill_github, df_gap = load_data()
except Exception as e:
    st.error(f"Gagal memuat data: {e}")
    st.stop()

# HEADER
st.title("SkillBridge AI — Skill Gap Dashboard")
st.markdown("**Analisis Kesenjangan Kompetensi: Standar SKKNI vs JobStreet Indonesia**")
st.caption(
    f"Dataset SKKNI: {len(df_skkni)} baris · "
    f"Dataset JobStreet Indonesia: {len(df_github)} lowongan · "
    f"Refresh: {datetime.now().strftime('%H:%M:%S')}"
)
st.markdown("---")

# SIDEBAR
st.sidebar.header("⚙️ Kontrol Dashboard")
st.sidebar.success(f"Last update: {datetime.now().strftime('%H:%M:%S')}")

list_jabatan = sorted(df_skkni["Jabatan"].dropna().unique().tolist())
selected_job = st.sidebar.selectbox(
    "Filter Jabatan",
    ["Semua Jabatan"] + list_jabatan
)

top_n = st.sidebar.slider("Jumlah Top Skill Ditampilkan", 1, 5, 5)

menu = st.sidebar.radio(
    "Pilih Halaman",
    [
        "Overview Jabatan",
        "Unit Kompetensi SKKNI",
        "Skill Demand Industri",
        "Gap Analysis"
    ]
)
st.sidebar.markdown("---")
st.sidebar.caption(
    "Sumber data:\n"
    "-SKKNI & JobStreet Indonesia\n"
)

# METRIC CARDS
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Jabatan SKKNI", df_skkni["Jabatan"].nunique())
with c2:
    st.metric("Total Baris SKKNI", f"{len(df_skkni):,}")
with c3:
    st.metric("Lowongan Kerja (JobStreet Indonesia)", f"{len(df_github):,}")
with c4:
    total_rel = (df_gap["Status"] == "Relevan").sum()
    pct_rel   = round(total_rel / len(df_gap) * 100, 1)
    st.metric("Skill SKKNI Relevan di Industri", f"{pct_rel}%")

st.markdown("---")

#OVERVIEW SEMUA
if menu == "Overview Jabatan":

    st.subheader("Overview Semua Jabatan SKKNI")

    overview = (
    df_skkni.groupby("Jabatan")
    .agg(
        Total_Baris=("Judul Unit", "count"),
        Unit_Unik=("Judul Unit", "nunique"),
        Elemen_Unik=("Elemen Kompetensi", "nunique"),
    )
    .reset_index()
    .sort_values("Total_Baris", ascending=False)
    .head(top_n)
    .rename(columns={
        "Jabatan":      "Jabatan",
        "Total_Baris":  "Total Baris",
        "Unit_Unik":    "Unit Kompetensi Unik",
        "Elemen_Unik":  "Elemen Kompetensi Unik",
    })
    .reset_index(drop=True)
)

    overview.index += 1

    col_ov1, col_ov2 = st.columns([1.2, 1])

    with col_ov1:
        st.dataframe(overview, use_container_width=True)

    with col_ov2:
        fig_ov, ax_ov = plt.subplots(figsize=(6, 4))

        colors_ov = sns.color_palette("Blues_d", len(overview))

        bars_ov = ax_ov.barh(
            overview["Jabatan"],
            overview["Total Baris"],
            color=colors_ov
        )

        ax_ov.bar_label(
            bars_ov,
            fmt="%d",
            padding=4,
            fontsize=11,
            fontweight="bold"
        )

        ax_ov.set_xlabel("Total Baris")

        ax_ov.set_title(
            "Distribusi Baris per Jabatan",
            fontsize=12,
            fontweight="bold"
        )

        ax_ov.invert_yaxis()

        ax_ov.set_xlim(
            0,
            overview["Total Baris"].max() + 15
        )

        plt.tight_layout()
        st.pyplot(fig_ov)


# FILTER
if selected_job != "Semua Jabatan":
    df_gap_f = df_gap[df_gap["Jabatan"] == selected_job].copy()
else:
    df_gap_f = df_gap.copy()

# JUMLAH UNIT KOMPETENSI PER JABATAN (SKKNI)
if menu == "Unit Kompetensi SKKNI":
    st.subheader("Jumlah unit kompetensi tiap jabatan di SKKNI")
    st.markdown(
        "Jumlah unit kompetensi mencerminkan **kompleksitas standar** "
        "yang ditetapkan SKKNI untuk masing-masing jabatan. "
        "Semakin banyak unit, semakin banyak kompetensi yang harus dikuasai."
    )

    col1, col2 = st.columns([1.4, 1])

    with col1:
        fig, ax = plt.subplots(figsize=(8, 5))
        colors = sns.color_palette("Blues_d", len(unit_per_job))
        unit_top = unit_per_job.head(top_n)
        bars = ax.barh(
            unit_per_job["Jabatan"],
            unit_per_job["Total Unit"],
            color=colors
        )
        ax.bar_label(bars, fmt="%d unit", padding=5, fontsize=11, fontweight="bold")
        ax.set_xlabel("Jumlah Unit Kompetensi Unik")
        ax.set_title("Kompleksitas Jabatan Berdasarkan Standar SKKNI",
                     fontsize=13, fontweight="bold")
        ax.invert_yaxis()
        ax.set_xlim(0, unit_per_job["Total Unit"].max() + 8)
        plt.tight_layout()
        st.pyplot(fig)

    with col2:
        st.markdown("#### Tabel ringkasan")
        st.dataframe(
            unit_top.rename(
                columns={
                    "Jabatan": "Jabatan",
                    "Total Unit": "Unit Kompetensi"
            }
        ),
        use_container_width=True,
        hide_index=True
        )
        top = unit_per_job.iloc[0]
        bot = unit_per_job.iloc[-1]
        st.info(
            f"**{top['Jabatan']}** paling kompleks dengan **{top['Total Unit']} unit** kompetensi.\n\n"
            f"**{bot['Jabatan']}** paling ringkas dengan **{bot['Total Unit']} unit** kompetensi."
        )

    if selected_job != "Semua Jabatan":
        st.markdown(f"#### Detail unit kompetensi: {selected_job}")
        detail = (
            df_skkni[df_skkni["Jabatan"] == selected_job][["Judul Unit"]]
            .drop_duplicates()
            .reset_index(drop=True)
        )
        detail.index += 1
        st.dataframe(detail, use_container_width=True)

# SKILL DEMAND INDUSTRI (GITHUB)
elif menu == "Skill Demand Industri":
    st.subheader("Skill yang paling sering diminta perusahaan di Indonesia")
    st.markdown(
        "Data diekstrak dari kolom **requirement** pada dataset lowongan kerja nyata & Menggambarkan kondisi permintaan pasar saat ini."
    )

    col1, col2 = st.columns([1.4, 1])

    with col1:
        st.markdown(f"#### Top {top_n} skill paling dicari industri")
        data_plot = df_skill_github.head(top_n)
        palette   = sns.color_palette("viridis", top_n)
        fig2, ax2 = plt.subplots(figsize=(8, 6))
        bars2 = ax2.barh(data_plot["Skill"], data_plot["Frekuensi"], color=palette)
        ax2.bar_label(bars2, fmt="%d", padding=4, fontsize=10)
        ax2.set_xlabel("Frekuensi Kemunculan di Lowongan")
        ax2.set_title(f"Top {top_n} Skill Demand — Pasar Kerja Indonesia",
                      fontsize=13, fontweight="bold")
        ax2.invert_yaxis()
        ax2.set_xlim(0, data_plot["Frekuensi"].max() + 15)
        plt.tight_layout()
        st.pyplot(fig2)

    with col2:
        st.markdown("#### Distribusi tipe pekerjaan")
        type_counts = df_github["type_of_work"].dropna().value_counts().head(5)
        fig3, ax3 = plt.subplots(figsize=(5, 5))
        ax3.pie(
            type_counts.values,
            labels=type_counts.index,
            autopct="%1.1f%%",
            startangle=140,
            colors=sns.color_palette("pastel")
        )
        ax3.set_title("Tipe Pekerjaan", fontsize=12, fontweight="bold")
        plt.tight_layout()
        st.pyplot(fig3)

        st.markdown("#### Rata-rata pengalaman yang dibutuhkan")
        avg_min = round(df_github["min_work_experience"].mean(), 1)
        avg_max = round(df_github["max_work_experience"].mean(), 1)
        st.metric("Min pengalaman rata-rata", f"{avg_min} tahun")
        st.metric("Max pengalaman rata-rata", f"{avg_max} tahun")

    st.success(
        f"Skill **{df_skill_github.iloc[0]['Skill']}** adalah yang paling banyak "
        f"diminta di pasar kerja Indonesia berdasarkan dataset acuan."
    )

# GAP ANALYSIS: SKKNI VS GITHUB
elif menu == "Gap Analysis":
    st.subheader("Gap Analysis: Skill SKKNI vs Kebutuhan Industri Nyata")
    st.markdown(
        "Setiap unit kompetensi SKKNI dicocokkan dengan skill yang muncul "
        "di lowongan kerja nyata. Status **Relevan** berarti ada kecocokan kata kunci "
        "dengan requirement industri. Status **Gap** berarti unit kompetensi tersebut "
        "belum terdeteksi di permintaan pasar."
    )

    # Summary per jabatan
    summary = (
        df_gap_f
        .groupby("Jabatan")
        .apply(lambda x: pd.Series({
            "Total Skill SKKNI": len(x),
            "Relevan":           (x["Status"] == "Relevan").sum(),
            "Gap":               (x["Status"] == "Gap (tidak ditemukan)").sum(),
        }))
        .reset_index()
    )
    summary["% Relevan"] = (
        summary["Relevan"] / summary["Total Skill SKKNI"] * 100
    ).round(1)
    summary = (
    summary
    .sort_values("% Relevan", ascending=False)
    .head(top_n)
    )
    col1, col2 = st.columns([1.4, 1])

    with col1:
        st.markdown("#### % skill SKKNI yang relevan dengan kebutuhan industri")
        fig4, ax4 = plt.subplots(figsize=(8, 5))
        colors_gap = ["#2ecc71" if v >= 50 else "#e74c3c"
                      for v in summary["% Relevan"]]
        bars4 = ax4.barh(summary["Jabatan"], summary["% Relevan"], color=colors_gap)
        ax4.bar_label(bars4, fmt="%.1f%%", padding=5, fontsize=11, fontweight="bold")
        ax4.axvline(x=50, color="gray", linestyle="--", linewidth=1,
                    label="Threshold 50%")
        ax4.set_xlabel("% Skill Relevan dengan Industri")
        ax4.set_title("Relevansi Kompetensi SKKNI vs JobStreet Indonesia",
                      fontsize=13, fontweight="bold")
        ax4.set_xlim(0, 115)
        ax4.invert_yaxis()
        ax4.legend()
        hijau = mpatches.Patch(color="#2ecc71", label="≥ 50% relevan")
        merah = mpatches.Patch(color="#e74c3c", label="< 50% relevan")
        ax4.legend(handles=[hijau, merah], loc="lower right")
        plt.tight_layout()
        st.pyplot(fig4)

    with col2:
        st.markdown("#### Tabel ringkasan gap per jabatan")
        st.dataframe(
            summary[["Jabatan", "Total Skill SKKNI", "Relevan", "Gap", "% Relevan"]],
            use_container_width=True,
            hide_index=True
        )
        best  = summary.loc[summary["% Relevan"].idxmax()]
        worst = summary.loc[summary["% Relevan"].idxmin()]
        st.success(
            f"**{best['Jabatan']}** paling relevan "
            f"({best['% Relevan']}% skill match dengan industri)."
        )
        st.warning(
            f"**{worst['Jabatan']}** perlu perhatian "
            f"({worst['% Relevan']}% skill match — gap terbesar)."
        )

# FOOTER
st.markdown("---")
st.caption(
    "SkillBridge AI Dashboard · Skill Gap Analysis: SKKNI vs JobStreet Indonesia · "
    f"Update: {datetime.now().strftime('%d %B %Y, %H:%M')}"
)