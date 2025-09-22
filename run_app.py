import os
import uvicorn

# Imposta la variabile d'ambiente SECRET_KEY
os.environ['SECRET_KEY'] = 'HneL62FmWHWUjV67T9m6fYhHPJC3Gs4sbhPiF5V5PeU'

# Avvia l'applicazione
if __name__ == "__main__":
    from web_new import app
    uvicorn.run(app, host="127.0.0.1", port=8080)