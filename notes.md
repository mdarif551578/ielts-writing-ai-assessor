
pip install -r requirements.txt








https://script.google.com/macros/s/AKfycbwQcAUXYdKmyXU6-jMBmTSLI_V49zJuA2rOp_BHYZ0hVIByP2w7mgfswEuMin-PWGcX/exec?key=VL2nHutEFnlCR9V2UTkzAWLGyspUhXFXlajiKzHVV9UONuq2&to=mda510624@yopmail.com&replyTo=mda510624@gmail.com&subject=Hello&htmlBody=Test+message



uvicorn main:app --reload



from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image
from io import BytesIO

app = FastAPI()

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    # Read file contents
    contents = await file.read()
    
    # Open image with Pillow
    img = Image.open(BytesIO(contents))
    
    # (Optional) process the image, e.g., get size
    width, height = img.size
    
    return JSONResponse(content={"filename": file.filename, "width": width, "height": height})

