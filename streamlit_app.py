import streamlit as st
import time
from openai import OpenAI
from deepgram import Deepgram
import tempfile
from streamlit.components.v1 import html

OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
DG_API_KEY = st.secrets["DG_API_KEY"]

openai_client = OpenAI(api_key=OPENAI_API_KEY)
dg_client = Deepgram(DG_API_KEY)

st.title("AI Interview Practice")

job_title = st.text_input("Enter the job position that you are interviewing for:")

if st.button("Generate Interview Question") and job_title.strip() != "":
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"Generate one interview question for {job_title}"}]
    )
    st.session_state["question"] = response.choices[0].message.content
    st.session_state["prep_done"] = False

if "question" in st.session_state:
    st.subheader("Question:")
    st.write(st.session_state["question"])

    if not st.session_state.get("prep_done", False):
        with st.empty():
            for sec in range(30, 0, -1):
                st.write(f"⏳ Prepare your answer: {sec} seconds left")
                time.sleep(1)
            st.session_state["prep_done"] = True
        st.write("You can now record your answer or type it.")

if st.session_state.get("prep_done", False):
    input_method = st.radio("Choose your answer input method:", ("Type Answer", "Record Audio"))

    transcription = ""
    
    if input_method == "Type Answer":
        transcription = st.text_area("Type your answer here:")
    
    elif input_method == "Record Audio":
        html_code = """
        <script>
        let recorder;
        let audioChunks = [];

        async function startRecording() {
            audioChunks = [];
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            recorder = new MediaRecorder(stream);
            recorder.ondataavailable = e => audioChunks.push(e.data);
            recorder.start();
            document.getElementById("status").innerText = "Recording...";
        }

        async function stopRecording() {
            recorder.stop();
            recorder.onstop = async () => {
                document.getElementById("status").innerText = "Saving file...";
                const blob = new Blob(audioChunks, { type: 'audio/wav' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'answer.wav';
                a.click();
                document.getElementById("status").innerText = "Recording saved. Please upload below.";
            }
        }
        </script>
        <button onclick="startRecording()">🎙️ Start Recording</button>
        <button onclick="stopRecording()">⏹️ Stop Recording</button>
        <p id="status">Press start to record</p>
        """
        html(html_code, height=150)

        uploaded_audio = st.file_uploader("Upload your recorded answer (WAV format)", type=["wav"])
        if uploaded_audio is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmpfile:
                tmpfile.write(uploaded_audio.read())
                audio_path = tmpfile.name

            with open(audio_path, "rb") as f:
                source = {"buffer": f, "mimetype": "audio/wav"}
                dg_response = dg_client.transcription.sync_prerecorded(source, {"punctuate": True})
                transcription = dg_response["results"]["channels"][0]["alternatives"][0]["transcript"]
            st.write("**Your Answer (Transcribed):**")
            st.write(transcription)
    
    if transcription and st.button("Get Feedback"):
        feedback_prompt = f"You are an expert interview coach. Give constructive feedback on this answer:\n{transcription}"
        feedback = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": feedback_prompt}]
        )
        st.subheader("Feedback:")
        st.write(feedback.choices[0].message.content)
