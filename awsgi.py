import uvicorn

if __name__ == '__main__':
    uvicorn.run("main:app", host="localhost", port=3001, reload=True, reload_delay=2)
