import google.generativeai as genai
from PIL import Image
import rich
import json
from prompt import ASSESSOR_PROMPT




def configure_model():
    global model
    genai.configure(api_key="AIzaSyDtPOZPVSC7YS3je1GdXGoQE2PtJE2vBl8")
    model = genai.GenerativeModel("models/gemini-2.0-flash")


def list_models():
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)


def get_question_text() -> str:
    question_img = Image.open('./images/question.jpg')
    response = model.generate_content(
        [
            "You are given an IELTS Writing Task 2 question paper image. Describe it completely and accurately. \
            Focus only on the task itself: state any images, diagrams, or text shown, and clearly extract the exact essay question or instruction. \
            Do not give explanations, strategies, or tips—only describe what the question paper asks the candidate to do.",
            question_img
        ]
    )
    response.resolve()
    return response.text


def get_answer_text() -> str:
    answer_imgs = [
        Image.open('./images/answer_1.jpg'),
        Image.open('./images/answer_2.jpg')
    ]
    response = model.generate_content(
        [
            "You are given an image of a handwritten IELTS Writing Task 2 answer sheet. \
            Read the handwriting carefully and transcribe it exactly into text. \
            Preserve the original spelling, grammar, punctuation, and paragraph breaks as written by the candidate. \
            Do not evaluate, summarize, or correct the answer — only provide a faithful transcription of the handwritten response.",
            *answer_imgs
        ]
    )
    response.resolve()
    return response.text


def get_task_evaluation(question, answer):
    CANDIDATE_ESSAY = f"""
    This is the Writing Task:
    {question}
    This is the Candidate Essay:
    {answer}
    """

    response = model.generate_content(
        [
            ASSESSOR_PROMPT,
            f"Candidate essay:\n\n{CANDIDATE_ESSAY}\n\n"
            "Now provide the assessment strictly in valid JSON format as defined in the output schema."
        ]
    )
    response.resolve()

    text = response.text
    if text.startswith("```json"):
        text = text[len("```json"):].strip()
    if text.endswith("```"):
        text = text[:-3].strip()

    # Attempt to parse JSON safely
    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        print("⚠️ Model did not return valid JSON, returning raw text.")
        return text
    
    return result





configure_model()

# question = get_question_text()
# answer = get_answer_text()

question = """
The image shows an IELTS Writing Task 2 question.

The text prompts the candidate to spend about 40 minutes on the task and to write about the following topic: "The most important aim of     
science should be to improve people's lives. To what extent do you agree or disagree with this statement?"

The text further instructs the candidate to give reasons for their answer and include any relevant examples from their own knowledge or     
experience, and to write at least 250 words. The statement "The most important aim of science should be to improve people's lives. To what  
extent do you agree or disagree with this statement?" is enclosed in a box.
"""
answer = """
Here is the transcription of the handwritten IELTS Writing Task 2 answer sheet:

Writing task 2

Science in an vital aspect of modern world where we live in. It plays an important role in our everyday life, from our basics to the most   
advanced things we use. Science is applicable almost everywhere. It is an irreplaceable part of our life. I agree withe the statement "The  
most important aim of science should be to improve people's lives".

To begin with, science is used in various things like innovation, opreservation and to discover new things as well. Yes, it is important to 
discover and preserve many things like rare animal or plants. But the top most priority of science should be to improve people's lives as itwill lead to making human life easy and convenient which will help humans to work more efficiently. As the human works efficiently, we will 
have power to develop and evolve. This will impact greatly for our upcoming generations.

As science will be focusing on improving people's lives, it will automatically lead to various good things that can be done. So improving   
people's life will increase the productivity of individuals and help them work efficiently. for eg. We can develop a tool which can organizeyour documents in the office and you can have access to them whenever you want. or you can make understand what people need and

You can deliver it to them. All these things will help people grow and evolve.

To recapitulate, improving peoples' life will help in all the aspects that needed. So, improving people's life should be the top most       
priority of science which will impact our lives massively.
"""

rich.print(question)
rich.print(answer)

evaluation = get_task_evaluation(question, answer)

rich.print(evaluation)

with open("result.json", "w", encoding="utf-") as f:
    f.write(json.dumps(evaluation))
