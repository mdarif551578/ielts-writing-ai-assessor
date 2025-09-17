from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from typing import List, Optional
from PIL import Image
from io import BytesIO
import google.generativeai as genai
import json
import asyncio
from prompt import ASSESSOR_PROMPT

app = FastAPI()

# Configure Gemini (use environment variable in production)
genai.configure(api_key="AIzaSyDtPOZPVSC7YS3je1GdXGoQE2PtJE2vBl8")
model = genai.GenerativeModel("models/gemini-2.0-flash")

async def get_text_from_images(files: List[UploadFile], is_question: bool) -> str:
    pil_images = []
    for file in files:
        contents = await file.read()
        img = Image.open(BytesIO(contents))
        pil_images.append(img)
    
    if is_question:
        prompt = """
        You are given an IELTS Writing Task question paper image(s). Describe it completely and accurately. 
        Focus only on the task itself: state any images, diagrams, or text shown, and clearly extract the exact essay question or instruction. 
        Do not give explanations, strategies, or tips—only describe what the question paper asks the candidate to do.
        """
    else:
        prompt = """
        You are given image(s) of a handwritten IELTS Writing Task answer sheet. 
        Read the handwriting carefully and transcribe it exactly into text. 
        Preserve the original spelling, grammar, punctuation, and paragraph breaks as written by the candidate. 
        Do not evaluate, summarize, or correct the answer — only provide a faithful transcription of the handwritten response.
        """
    
    response = await asyncio.to_thread(model.generate_content, [prompt] + pil_images)
    response.resolve()
    return response.text

async def get_task_evaluation(question: str, answer: str, task_type: str, name: Optional[str] = None, email: Optional[str] = None):
    name = name or "Anonymous"
    email = email or ""
    
    CANDIDATE_ESSAY = f"""
    Candidate Name: {name}
    Candidate Email: {email}
    This is the Writing Task Type: {task_type}
    This is the Writing Task:
    {question}
    This is the Candidate Essay:
    {answer}
    """
    
    response = await asyncio.to_thread(model.generate_content, [
        ASSESSOR_PROMPT,
        f"Candidate essay:\n\n{CANDIDATE_ESSAY}\n\n"
        "Now provide the assessment strictly in valid JSON format as defined in the output schema."
    ])
    response.resolve()

    text = response.text
    if text.startswith("```json"):
        text = text[len("```json"):].strip()
    if text.endswith("```"):
        text = text[:-3].strip()

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        return {"error": "Model did not return valid JSON", "raw_text": text}
    
    return result

@app.post("/assess/")
async def assess(
    task_type: str = Form(...),
    question_text: Optional[str] = Form(None),
    question_images: List[UploadFile] = File(None),
    answer_text: Optional[str] = Form(None),
    answer_images: List[UploadFile] = File(None),
    name: Optional[str] = Form(None),
    email: Optional[str] = Form(None)
):
    if question_text:
        question = question_text
    elif question_images:
        question = await get_text_from_images(question_images, True)
    else:
        return JSONResponse(content={"error": "Provide question text or images"}, status_code=400)

    if answer_text:
        answer = answer_text
    elif answer_images:
        answer = await get_text_from_images(answer_images, False)
    else:
        return JSONResponse(content={"error": "Provide answer text or images"}, status_code=400)

    evaluation = await get_task_evaluation(question, answer, task_type, name, email)
    
    return JSONResponse(content=evaluation)






