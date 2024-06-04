import base64
import io
from pypdf import PdfReader #replace with something from ai packages, or not?
import importlib.util
import sys
#from PyPDF2 import PdfReader #try and compare

def parseBase64PdfText(pdfBase64String : str) -> str:
    try:
        pdf_file = base64.b64decode(pdfBase64String)
        pdf_file_text = ""
        reader = PdfReader(io.BytesIO(pdf_file))
        for page in reader.pages:
            pdf_file_text += page.extract_text()
        return pdf_file_text
    except Exception as exc:
        return f"Error parsing pdf file: {exc}"
    
def pruneLargeObjectForPrinting(object) -> str:
    return pruneLongTextForPrinting(str(object))
        
def pruneLongTextForPrinting(text : str) -> str:
    if (len(text) > 500):
        return text[:300] + " ... long string ... " + text[-150:]
    else:
        return text
            
def importByName(name, package=None):
    """An approximate implementation of import."""
    absolute_name = importlib.util.resolve_name(name, package)
    try:
        return sys.modules[absolute_name]
    except KeyError:
        pass

    path = None
    if '.' in absolute_name:
        parent_name, _, child_name = absolute_name.rpartition('.')
        parent_module = importByName(parent_name)
        path = parent_module.__spec__.submodule_search_locations
    for finder in sys.meta_path:
        spec = finder.find_spec(absolute_name, path)
        if spec is not None:
            break
    else:
        msg = f'No module named {absolute_name!r}'
        raise ModuleNotFoundError(msg, name=absolute_name)
    module = importlib.util.module_from_spec(spec)
    sys.modules[absolute_name] = module
    spec.loader.exec_module(module)
    if path is not None:
        setattr(parent_module, child_name, module)
    return module
