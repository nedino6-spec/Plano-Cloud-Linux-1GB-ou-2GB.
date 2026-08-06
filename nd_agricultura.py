"""Aplicativo simples para importar pontos de latitude/longitude em CSV."""

import tkinter as tk
from tkinter import filedialog, messagebox

pontos = []


def importar():
    """Importa pontos de um arquivo CSV com colunas lat,lng."""
    global pontos
    path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
    if not path:
        return

    pts = []
    try:
        with open(path, encoding="utf-8") as arquivo:
            next(arquivo)
            for linha in arquivo:
                lat, lng = linha.strip().split(",")
                pts.append((float(lat), float(lng)))

        pontos = pts
        messagebox.showinfo("OK", f"{len(pontos)} pontos carregados")

    except Exception as exc:
        messagebox.showerror("Erro", str(exc))


def testar():
    """Mostra se o sistema já recebeu pontos importados."""
    if not pontos:
        messagebox.showwarning("Aviso", "Importe primeiro")
    else:
        messagebox.showinfo("OK", "Sistema funcionando!")


def criar_janela():
    """Cria e retorna a janela principal do aplicativo."""
    root = tk.Tk()
    root.title("ND Agricultura de Precisão")
    root.geometry("400x200")

    tk.Button(root, text="Importar CSV", command=importar).pack(pady=20)
    tk.Button(root, text="Testar Sistema", command=testar).pack(pady=20)

    return root


if __name__ == "__main__":
    criar_janela().mainloop()
