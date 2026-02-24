from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .files import create_file, create_folder, delete_item, list_files, read_text_file, write_text_file


router = APIRouter()


class FileContent(BaseModel):
    path: str
    content: str


class CreateFile(BaseModel):
    path: str
    content: str = ""


class CreateFolder(BaseModel):
    path: str


@router.get("/api/files/list")
async def list_files_endpoint(path: str = ""):
    try:
        items = list_files(path)
        return {"items": items, "path": path}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/files/read")
async def read_file_endpoint(path: str):
    try:
        content = read_text_file(path)
        return {"content": content, "path": path}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/api/files/write")
async def write_file_endpoint(file_data: FileContent):
    try:
        write_text_file(file_data.path, file_data.content)
        return {"success": True, "path": file_data.path}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/api/files/create")
async def create_file_endpoint(create_data: CreateFile):
    try:
        safe_path = create_file(create_data.path, create_data.content)
        return {"success": True, "path": str(safe_path)}
    except FileExistsError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/api/files/folder")
async def create_folder_endpoint(folder_data: CreateFolder):
    try:
        safe_path = create_folder(folder_data.path)
        return {"success": True, "path": str(safe_path)}
    except FileExistsError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/api/files/delete")
async def delete_item_endpoint(path: str):
    try:
        delete_item(path)
        return {"success": True, "path": path}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
