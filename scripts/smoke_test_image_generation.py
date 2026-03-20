import asyncio
import os
from pathlib import Path

async def main():
    try:
        from tools.image_generation_tool import ImageGenerationTool
    except Exception as e:
        print('IMPORT_ERROR', e)
        return
    tool = ImageGenerationTool()
    print('Running ImageGenerationTool...')
    url = await tool.run('smoke test image generation of a friendly cat')
    print('Returned URL:', url)
    if url and url.startswith('/media/images/'):
        fname = url.split('/media/images/')[-1]
        repo_root = Path(__file__).resolve().parent.parent
        fpath = repo_root / 'media' / 'images' / fname
        print('Checking file path:', fpath)
        exists = fpath.exists()
        size = fpath.stat().st_size if exists else None
        print('Exists:', exists, 'Size:', size)
    else:
        print('URL was not a local media path; full value:', url)

if __name__ == '__main__':
    asyncio.run(main())
