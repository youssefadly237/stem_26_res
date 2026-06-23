import streamlit as st
import pandas as pd
import altair as alt

CSV_PATH = "stem_results.csv"

SCIENCE_SUBJECTS = [
    ("arabic", "arabic_grade", "arabic_points"),
    ("first_language", "first_language_grade", "first_language_points"),
    ("second_language", None, None),
    ("chemistry", "chemistry_grade", "chemistry_points"),
    ("physics", "physics_grade", "physics_points"),
    ("biology", "biology_grade", "biology_points"),
    ("geology", "geology_grade", "geology_points"),
]

MATH_SUBJECTS = [
    ("arabic", "arabic_grade", "arabic_points"),
    ("first_language", "first_language_grade", "first_language_points"),
    ("second_language", None, None),
    ("chemistry", "chemistry_grade", "chemistry_points"),
    ("physics", "physics_grade", "physics_points"),
    ("pure_math", "pure_math_grade", "pure_math_points"),
    ("applied_math", "applied_math_grade", "applied_math_points"),
]


@st.cache_data
def load_data():
    df = pd.read_csv(CSV_PATH, dtype={"seat_number": str, "national_id": str})
    df = df[df["status"] != "not_found"].copy()
    df["gpa"] = pd.to_numeric(df["gpa"], errors="coerce")

    df["second_language_grade"] = df.apply(
        lambda r: (
            r["french_grade"] if r["second_language"] == "French" else r["german_grade"]
        ),
        axis=1,
    )
    df["second_language_points"] = pd.to_numeric(
        df.apply(
            lambda r: (
                r["french_points"]
                if r["second_language"] == "French"
                else r["german_points"]
            ),
            axis=1,
        ),
        errors="coerce",
    )

    return df


def compute_subject_ranks(df):
    df = df.copy()
    points_cols = [c for c in df.columns if c.endswith("_points")]
    for col in points_cols:
        if df[col].notna().any():
            rank_col = f"{col}_rank"
            tie_col = f"{col}_rank_ties"
            df[rank_col] = (
                df.groupby("branch")[col]
                .rank(ascending=False, method="min")
                .astype("Int64")
            )
            df[tie_col] = (
                df.groupby(["branch", rank_col])[col].transform("size").astype("Int64")
            )

    df["total_count"] = df.groupby("branch")["seat_number"].transform("count")
    df["gpa_rank"] = (
        df.groupby("branch")["gpa"].rank(ascending=False, method="min").astype("Int64")
    )
    df["gpa_rank_ties"] = (
        df.groupby(["branch", "gpa_rank"])["gpa"].transform("size").astype("Int64")
    )
    return df


def get_subject_label(name):
    labels = {
        "arabic": "Arabic",
        "first_language": "English",
        "second_language": "2nd Language",
        "chemistry": "Chemistry",
        "physics": "Physics",
        "biology": "Biology",
        "geology": "Geology",
        "pure_math": "Pure Math",
        "applied_math": "Applied Math",
    }
    return labels.get(name, name)


def subjects_for_branch(branch):
    return SCIENCE_SUBJECTS if branch == "Science" else MATH_SUBJECTS


def paginate(items, page_size, page):
    total = len(items)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = min(page, total_pages)
    start = (page - 1) * page_size
    page_data = items.iloc[start : start + page_size]
    return page_data, total_pages


def render_student_card(row, subjects):
    total = int(row["total_count"])
    gpa_ties = int(row["gpa_rank_ties"])
    tie_text = (
        f" (tied with {gpa_ties - 1} other{'s' if gpa_ties - 1 != 1 else ''})"
        if gpa_ties > 1
        else ""
    )

    rows = []
    for name, grade_col, points_col in subjects:
        label = get_subject_label(name)
        if name == "second_language":
            grade = row.get("second_language_grade", "")
            points = row.get("second_language_points", "")
            rank_col = "second_language_points_rank"
            tie_col = "second_language_points_rank_ties"
        else:
            grade = row.get(grade_col, "")
            points = row.get(points_col, "")
            rank_col = f"{points_col}_rank"
            tie_col = f"{points_col}_rank_ties"

        rank_val = row.get(rank_col)
        tie_val = row.get(tie_col)
        rank = int(rank_val) if pd.notna(rank_val) else None
        ties = int(tie_val) if pd.notna(tie_val) else 1

        points_str = (
            f"{points:.1f}"
            if isinstance(points, (int, float)) and not pd.isna(points)
            else "-"
        )
        grade_str = str(grade) if pd.notna(grade) else "-"
        rank_display = (
            f"#{rank}" if rank and ties <= 1 else (f"#{rank} ({ties})" if rank else "-")
        )

        rows.append(
            {
                "Subject": label,
                "Grade": grade_str,
                "Points": points_str,
                "Rank": rank_display,
            }
        )

    table_df = pd.DataFrame(rows)

    with st.container(border=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"### {row['english_name']}")
            st.markdown(f"*{row['arabic_name']}*")
            st.markdown(
                f"Seat `{row['seat_number']}` · Branch `{row['branch']}` · {row['school_en']}"
            )
        with col2:
            st.html(
                f"""<div style="text-align:center;background:var(--secondary-background-color);border-radius:10px;padding:12px">
<div style="font-size:13px;opacity:0.7">Overall Rank</div>
<div style="font-size:30px;font-weight:700">#{int(row["gpa_rank"])}</div>
<div style="font-size:13px;opacity:0.7">of {total}{tie_text}</div>
<div style="font-size:14px;margin-top:4px;font-weight:600">GPA {row["gpa"]}</div>
</div>"""
            )

        st.markdown("**Subject Ranks**")
        st.dataframe(
            table_df,
            column_config={
                "Subject": st.column_config.TextColumn("Subject"),
                "Grade": st.column_config.TextColumn("Grade", width="small"),
                "Points": st.column_config.TextColumn("Points", width="small"),
                "Rank": st.column_config.TextColumn("Rank", width="small"),
            },
            hide_index=True,
            width="stretch",
        )


def main():
    st.set_page_config(page_title="STEM 26 Results", layout="wide")
    st.title("STEM 26 Results")

    df = load_data()
    df = compute_subject_ranks(df)

    tab1, tab2, tab3 = st.tabs(["Search", "Rankings", "Stats"])

    with tab1:
        c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 1], vertical_alignment="center")
        with c1:
            query = st.text_input(
                "Search by name (Arabic/English) or seat number"
            ).strip()
        with c2:
            per_page = st.selectbox("Per page", [5, 10, 20, 50], index=1, key="s_size")

        if query:
            mask = (
                df["arabic_name"].str.contains(query, case=False, na=False)
                | df["english_name"].str.contains(query, case=False, na=False)
                | df["seat_number"].eq(query)
            )
            results = df[mask]
            _, total_pages = paginate(results, per_page, 1)
            with c3:
                if st.session_state.get("s_page", 1) > total_pages:
                    st.session_state["s_page"] = total_pages
                page_num = st.number_input(
                    "Page", min_value=1, max_value=total_pages, value=1, key="s_page"
                )
            page_data, total_pages = paginate(results, per_page, page_num)
            of_text = f"of {total_pages}" if total_pages > 1 else ""
            with c4:
                st.html(
                    f"<div style='padding-top:24px;text-align:center'>{of_text}</div>"
                )
            with c5:
                st.html(
                    f"<div style='padding-top:24px'><strong>{len(results)}</strong> result(s)</div>"
                )
            if results.empty:
                st.info("No results found.")
            else:
                for _, row in page_data.iterrows():
                    render_student_card(row, subjects_for_branch(row["branch"]))

    with tab2:
        c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1, 1], vertical_alignment="center")
        with c1:
            branch = st.selectbox("Branch", sorted(df["branch"].unique()), key="branch")
        with c2:
            per_page = st.selectbox("Per page", [5, 10, 20, 50], index=1, key="r_size")

        branch_df = df[df["branch"] == branch].sort_values("gpa_rank")
        _, total_pages = paginate(branch_df, per_page, 1)
        with c3:
            if st.session_state.get("r_page", 1) > total_pages:
                st.session_state["r_page"] = total_pages
            page_num = st.number_input(
                "Page", min_value=1, max_value=total_pages, value=1, key="r_page"
            )
        page_data, total_pages = paginate(branch_df, per_page, page_num)
        of_text = f"of {total_pages}" if total_pages > 1 else ""
        with c4:
            st.html(f"<div style='padding-top:24px;text-align:center'>{of_text}</div>")
        with c5:
            st.html(
                f"<div style='padding-top:24px'><strong>{len(branch_df)}</strong> student(s)</div>"
            )
        for _, row in page_data.iterrows():
            render_student_card(row, subjects_for_branch(row["branch"]))

    with tab3:
        branch_filter = st.selectbox(
            "Branch", ["All"] + sorted(df["branch"].unique()), key="stats_branch"
        )
        subj_df = df if branch_filter == "All" else df[df["branch"] == branch_filter]
        subjects = (
            SCIENCE_SUBJECTS + MATH_SUBJECTS
            if branch_filter == "All"
            else subjects_for_branch(branch_filter)
        )

        grade_order = [
            "A",
            "A-",
            "B+",
            "B",
            "B-",
            "C+",
            "C",
            "C-",
            "D+",
            "D",
            "D-",
            "F",
        ]
        seen = set()
        for name, grade_col, _ in subjects:
            if name in seen:
                continue
            seen.add(name)
            col = "second_language_grade" if name == "second_language" else grade_col
            counts = subj_df[col].value_counts()
            dist = pd.DataFrame({"grade": grade_order}).set_index("grade")
            dist["count"] = dist.index.map(lambda g: int(counts.get(g, 0)))

            st.markdown(f"**{get_subject_label(name)}**")
            chart = (
                alt.Chart(dist.reset_index())
                .mark_bar()
                .encode(
                    x=alt.X("grade:N", sort=None),
                    y=alt.Y("count:Q"),
                )
                .properties(height=200)
            )
            st.altair_chart(chart, width="stretch")

        gpa_bins = subj_df["gpa"].dropna()
        if not gpa_bins.empty:
            gpa_dist = gpa_bins.round(1).value_counts().sort_index().reset_index()
            gpa_dist.columns = ["GPA", "count"]
            st.markdown("**GPA Distribution**")
            chart = (
                alt.Chart(gpa_dist)
                .mark_bar()
                .encode(
                    x=alt.X("GPA:Q", scale=alt.Scale(domain=[0, 4])),
                    y=alt.Y("count:Q"),
                )
                .properties(height=200)
            )
            st.altair_chart(chart, width="stretch")


if __name__ == "__main__":
    main()
