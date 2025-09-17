from fastapi import FastAPI, File, UploadFile, Form, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import List, Optional
from PIL import Image
from io import BytesIO
import google.generativeai as genai
import json
import asyncio
from prompt import ASSESSOR_PROMPT
from dotenv import load_dotenv
import os
from fastapi.middleware.cors import CORSMiddleware
from typing import Union


load_dotenv()
app = FastAPI()
templates = Jinja2Templates(directory="templates")
# Allow CORS for all origins, methods, and headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or list of allowed origins, e.g. ["https://example.com"]
    allow_credentials=True,
    allow_methods=["*"],  # GET, POST, etc.
    allow_headers=["*"],  # Allow all headers
)


# Configure Gemini (use environment variable in production)
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("models/gemini-2.0-flash")

async def get_text_from_images(files: List[UploadFile], is_question: bool) -> str:
    if not files:
        return ""

    prompt = (
        """
        You are given an IELTS Writing Task question paper image(s). Describe it completely and accurately. 
        Focus only on the task itself: state any images, diagrams, or text shown, and clearly extract the exact essay question or instruction. 
        Do not give explanations, strategies, or tips—only describe what the question paper asks the candidate to do.
        """
        if is_question else
        """
        You are given image(s) of a handwritten IELTS Writing Task answer sheet. 
        Read the handwriting carefully and transcribe it exactly into text. 
        Preserve the original spelling, grammar, punctuation, and paragraph breaks as written by the candidate. 
        Do not evaluate, summarize, or correct the answer — only provide a faithful transcription of the handwritten response.
        """
    )

    results = []

    for idx, file in enumerate(files):
        contents = await file.read()
        img = Image.open(BytesIO(contents))

        # Call Gemini for each image individually
        response = await asyncio.to_thread(model.generate_content, [prompt, img])
        response.resolve()
        results.append(response.text.strip())

    # Combine results
    combined_text = "\n\n".join(results)
    return combined_text
    

async def get_task_evaluation(
    question: str, answer: str, task_type: str, name: Optional[str] = None, email: Optional[str] = None
):
    name = name or "Anonymous"
    email = email or ""
    
    candidate_essay = f"""
Candidate Name: {name}
Candidate Email: {email}
Writing Task Type: {task_type}
Writing Task:
{question}
Candidate Essay:
{answer}
"""

    response = await asyncio.to_thread(
        model.generate_content,
        [
            ASSESSOR_PROMPT,
            f"Candidate essay:\n\n{candidate_essay}\n\nNow provide the assessment strictly in valid JSON format as defined in the output schema."
        ]
    )
    response.resolve()

    text = response.text.strip()
    # Clean markdown formatting if present
    if text.startswith("```json"):
        text = text[len("```json"):].strip()
    if text.endswith("```"):
        text = text[:-3].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"error": "Model did not return valid JSON", "raw_text": text}


@app.post("/assess/")
async def assess(
    task_type: str = Form(...),
    question_text: Optional[str] = Form(None),
    question_images: Optional[Union[UploadFile, List[UploadFile]]] = File(None),
    answer_text: Optional[str] = Form(None),
    answer_images: Optional[Union[UploadFile, List[UploadFile]]] = File(None),
    name: Optional[str] = Form(None),
    email: Optional[str] = Form(None)
):
    # Normalize files to lists
    if question_images is None:
        question_images = []
    elif not isinstance(question_images, list):
        question_images = [question_images]

    if answer_images is None:
        answer_images = []
    elif not isinstance(answer_images, list):
        answer_images = [answer_images]

    # Ensure at least one input for question
    if not question_text and not question_images:
        return JSONResponse(content={"error": "Provide either question text or question images"}, status_code=400)
    # Ensure at least one input for answer
    if not answer_text and not answer_images:
        return JSONResponse(content={"error": "Provide either answer text or answer images"}, status_code=400)

    # Process question
    question = question_text or await get_text_from_images(question_images, is_question=True)
    # Process answer
    answer = answer_text or await get_text_from_images(answer_images, is_question=False)

    evaluation = await get_task_evaluation(question, answer, task_type, name, email)
    return JSONResponse(content=evaluation)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

