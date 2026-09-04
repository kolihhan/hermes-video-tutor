from __future__ import annotations

from pathlib import Path

from video_tutor.bootstrap import build_tutor_service
from video_tutor.course import load_course_manifest
from video_tutor.tutor import TutorService


def ask_tutor(service: TutorService, *, question: str, course_manifest: str | Path):
    return service.ask(question=question, course_manifest=course_manifest)


def main() -> None:
    import streamlit as st

    root = Path(__file__).resolve().parent
    manifest = root / "demo" / "course.json"
    course = load_course_manifest(manifest)
    service = build_tutor_service(repo_root=root)

    st.set_page_config(page_title="Hermes Video Tutor", layout="wide")
    st.title("Hermes Video Tutor")
    st.caption("Ask a lecture question. Hermes chooses transcript, frame, or clip evidence as needed.")

    left, right = st.columns([3, 2])
    with left:
        st.video(str(course.video_path))
    with right:
        question = st.text_input("Ask about this lecture")
        submitted = st.button("Ask", type="primary")

    if submitted and question.strip():
        with st.spinner("Collecting evidence..."):
            answer = ask_tutor(service, question=question, course_manifest=manifest)
        st.subheader("Answer")
        st.write(answer.text)

        activity_col, evidence_col = st.columns(2)
        with activity_col:
            st.subheader("Agent Activity")
            for event in answer.activity:
                st.write(f"**{event.tool}** — {event.summary}")
        with evidence_col:
            st.subheader("Evidence")
            for item in answer.evidence:
                st.markdown(f"**{item.evidence_id} · {item.kind} · {item.start_s:.1f}-{item.end_s:.1f}s**")
                st.write(item.text)
                for media_path in item.media_paths:
                    st.image(media_path)


if __name__ == "__main__":
    main()
