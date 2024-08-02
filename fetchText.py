from pyngrok import ngrok
import nest_asyncio
import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from io import BytesIO
import easyocr
import re

nest_asyncio.apply()

app = FastAPI()

reader = easyocr.Reader(['en'])

def recognize_text_from_image(image: BytesIO) -> str:
    try:
        image.seek(0)
        image_bytes = image.read()
        results = reader.readtext(image_bytes)
        extracted_text = "\n".join([result[1] for result in results])
        return extracted_text.strip()
    except Exception as e:
        print(f"Error in recognize_text_from_image: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def format_cnic(cnic: str) -> str:
    try:
        cnic = cnic.replace(" ", "").replace("-", "")
        if len(cnic) == 13:
            return f"{cnic[:5]}-{cnic[5:12]}-{cnic[12:]}"
        elif len(cnic) == 12:
            return f"{cnic[:5]}-{cnic[5:10]}-{cnic[10:]}"
        elif len(cnic) == 11:
            return f"{cnic[:5]}-{cnic[5:9]}-{cnic[9:]}"
        return "CNIC Not Found"
    except Exception as e:
        print(f"Error in format_cnic: {e}")
        return "CNIC Not Found"

def extract_name_and_cnic(text: str):
    try:
        
        text = re.sub(r'\b0m\b', '', text)  

        
        name_pattern = re.compile(r'(?:Name|Nama|NM|Holder)\s*[:\-\s]*(.*?)(?:\n|Father Name|Gender|Country|Identity)', re.IGNORECASE)
        cnic_pattern = re.compile(r'\b\d{5}[-\s]?\d{7}[-\s]?\d\b', re.IGNORECASE)

        
        cnic_matches = cnic_pattern.findall(text)
        if cnic_matches:
            cnic_candidates = [format_cnic(cnic) for cnic in cnic_matches]
            cnic = cnic_candidates[0]
        else:
            cnic = "CNIC Not Found"

        
        name_match = name_pattern.search(text)
        if name_match:
            name = name_match.group(1).strip()
            if name:
                name = re.sub(r'\s+', ' ', name).strip()
        else:
            name = "Name Not Found"

        return name, cnic
    except Exception as e:
        print(f"Error in extract_name_and_cnic: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class ExtractionResponse(BaseModel):
    name: str
    cnic: str

@app.post("/extract")
async def extract_info(file: UploadFile = File(...)) -> ExtractionResponse:
    try:
        print(f"Received file: {file.filename}, content type: {file.content_type}")

        content = await file.read()
        if not content:
            raise ValueError("File content is empty")

        image = BytesIO(content)

        print(f"File size: {len(content)} bytes")

        text = recognize_text_from_image(image)
        print(f"OCR Text: {text}")
        name, cnic = extract_name_and_cnic(text)
        return ExtractionResponse(name=name, cnic=cnic)
    except Exception as e:
        print(f"Error in extract_info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

public_url = ngrok.connect(8000)
print(f"Public URL: {public_url}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
