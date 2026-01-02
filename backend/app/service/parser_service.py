
from typing import Dict, List
from fastapi import UploadFile
import json
import logging
import mimetypes
import tempfile
import os
from fastapi import UploadFile
from pathlib import Path
from pydantic import ValidationError
from app.core.llamaindex import LlamaIndex, get_llama

logger = logging.getLogger(__name__)


class TextParser:
    @staticmethod
    def parse(path: str|Path,page_size=2000) -> List[Dict]:
        """
        Return text
        """
        with open(path, "rb") as f:
            text=f.read().decode("utf-8",errors="ignore")
            return [
                {"page": int(i/page_size)+1, "text": text[i : i + page_size]}
                for i in range(0, len(text), page_size)
            ]



class LLamaParser:
    @staticmethod
    async def parse(file_path: str|Path)->List[dict]:
        file_path = Path(file_path)


        # JSON output
        parser=await get_llama()
        docs = await parser.aload_data(str(file_path))
        print(docs)

        output=[{"page":idx+1,"text":i.text} for idx,i in enumerate(docs)]

        return output

class DocumentService:
    @staticmethod
    async def parse(file: UploadFile )->List[dict]:
        """ Validate if file is TXT, PDF and DOCX else raise ValueError """
        content_type = file.content_type or ""
        suffix = mimetypes.guess_extension(content_type) or ""
        tmp_path = None

        try:
            await file.seek(0)
            raw_bytes = await file.read()
            await file.seek(0)

            if not raw_bytes:
                raise ValidationError("Empty file")

            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(raw_bytes)
                tmp_path = tmp.name


            return await DocumentService.validate_file( content_type ,tmp_path)


        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass



    @staticmethod
    async def validate_file(content_type: str,path:str|Path):
        match content_type:
            case "text/plain":
                return TextParser.parse(path)
            case "application/pdf":
                return await LLamaParser.parse(path)
            case "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                return await LLamaParser.parse(path)
            case _:
                raise ValueError(f"Unsupported file type: {content_type}. Only TXT, PDF, and DOCX are allowed.")

 
    @staticmethod
    def upload_file(file_data):
        # Logic to upload file
        pass

    @staticmethod
    def get_file(file_id):
        # Logic to retrieve file
        pass








