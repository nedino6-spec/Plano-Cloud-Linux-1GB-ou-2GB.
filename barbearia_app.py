import sqlite3
import tkinter as tk
import urllib.parse
import webbrowser
from datetime import datetime
from tkinter import messagebox, ttk

DB_PATH = "barbearia.db"


class BarbeariaDB:
    def __init__(self, path=DB_PATH):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.criar_tabelas()

    def criar_tabelas(self):
        cur = self.conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                telefone TEXT NOT NULL,
                observacoes TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS barbeiros (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                ativo INTEGER DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS servicos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                preco REAL NOT NULL,
                duracao_min INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS agendamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id INTEGER NOT NULL,
                barbeiro_id INTEGER NOT NULL,
                servico_id INTEGER NOT NULL,
                data_hora TEXT NOT NULL,
                status TEXT DEFAULT 'Agendado',
                criado_em TEXT NOT NULL,
                FOREIGN KEY(cliente_id) REFERENCES clientes(id),
                FOREIGN KEY(barbeiro_id) REFERENCES barbeiros(id),
                FOREIGN KEY(servico_id) REFERENCES servicos(id)
            );
            CREATE TABLE IF NOT EXISTS fila (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id INTEGER NOT NULL,
                servico_id INTEGER NOT NULL,
                barbeiro_id INTEGER,
                chegada_em TEXT NOT NULL,
                status TEXT DEFAULT 'Aguardando',
                FOREIGN KEY(cliente_id) REFERENCES clientes(id),
                FOREIGN KEY(servico_id) REFERENCES servicos(id),
                FOREIGN KEY(barbeiro_id) REFERENCES barbeiros(id)
            );
            """
        )
        self.conn.commit()
        self.seed()

    def seed(self):
        cur = self.conn.cursor()
        if cur.execute("SELECT COUNT(*) FROM barbeiros").fetchone()[0] == 0:
            cur.executemany("INSERT INTO barbeiros(nome) VALUES(?)", [("Barbeiro 1",), ("Barbeiro 2",)])
        if cur.execute("SELECT COUNT(*) FROM servicos").fetchone()[0] == 0:
            cur.executemany(
                "INSERT INTO servicos(nome, preco, duracao_min) VALUES(?,?,?)",
                [("Corte", 40, 40), ("Barba", 30, 30), ("Corte + Barba", 65, 70)],
            )
        self.conn.commit()

    def add_cliente(self, nome, telefone, observacoes):
        self.conn.execute(
            "INSERT INTO clientes(nome, telefone, observacoes) VALUES(?,?,?)",
            (nome, telefone, observacoes),
        )
        self.conn.commit()

    def add_barbeiro(self, nome):
        self.conn.execute("INSERT INTO barbeiros(nome) VALUES(?)", (nome,))
        self.conn.commit()

    def add_servico(self, nome, preco, duracao):
        self.conn.execute("INSERT INTO servicos(nome, preco, duracao_min) VALUES(?,?,?)", (nome, preco, duracao))
        self.conn.commit()

    def rows(self, sql, params=()):
        return self.conn.execute(sql, params).fetchall()

    def executar(self, sql, params=()):
        self.conn.execute(sql, params)
        self.conn.commit()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.db = BarbeariaDB()
        self.title("Gestão de Barbearia 2026")
        self.geometry("1120x720")
        self.configure(bg="#101820")
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        self.combo_data = {}
        self.criar_abas()
        self.atualizar_tudo()

    def criar_abas(self):
        self.admin_tab = ttk.Frame(self.notebook)
        self.clientes_tab = ttk.Frame(self.notebook)
        self.agenda_tab = ttk.Frame(self.notebook)
        self.fila_tab = ttk.Frame(self.notebook)
        self.config_tab = ttk.Frame(self.notebook)
        for nome, tab in [
            ("Painel Admin", self.admin_tab),
            ("Clientes", self.clientes_tab),
            ("Agenda + WhatsApp", self.agenda_tab),
            ("Fila de Chegada", self.fila_tab),
            ("Serviços/Barbeiros", self.config_tab),
        ]:
            self.notebook.add(tab, text=nome)
        self.montar_admin()
        self.montar_clientes()
        self.montar_agenda()
        self.montar_fila()
        self.montar_config()

    def campo(self, parent, label, row, col=0):
        ttk.Label(parent, text=label).grid(row=row, column=col, sticky="w", padx=6, pady=4)
        ent = ttk.Entry(parent, width=34)
        ent.grid(row=row, column=col + 1, sticky="ew", padx=6, pady=4)
        return ent

    def montar_admin(self):
        self.cards = tk.StringVar()
        ttk.Label(self.admin_tab, textvariable=self.cards, font=("Arial", 16, "bold")).pack(anchor="w", padx=10, pady=10)
        self.admin_tree = self.tree(self.admin_tab, ["Tipo", "Cliente", "Serviço", "Barbeiro", "Data/Hora", "Status"])

    def montar_clientes(self):
        form = ttk.LabelFrame(self.clientes_tab, text="Novo cliente")
        form.pack(fill="x", padx=10, pady=8)
        self.cliente_nome = self.campo(form, "Nome", 0)
        self.cliente_tel = self.campo(form, "Telefone/WhatsApp", 1)
        self.cliente_obs = self.campo(form, "Observações", 2)
        ttk.Button(form, text="Salvar cliente", command=self.salvar_cliente).grid(row=3, column=1, sticky="e", padx=6, pady=8)
        self.clientes_tree = self.tree(self.clientes_tab, ["ID", "Nome", "Telefone", "Observações"])

    def montar_agenda(self):
        form = ttk.LabelFrame(self.agenda_tab, text="Novo agendamento")
        form.pack(fill="x", padx=10, pady=8)
        self.ag_cliente = self.combo(form, "Cliente", 0)
        self.ag_barbeiro = self.combo(form, "Barbeiro", 1)
        self.ag_servico = self.combo(form, "Serviço", 2)
        self.ag_data = self.campo(form, "Data e hora (AAAA-MM-DD HH:MM)", 3)
        self.ag_data.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M"))
        ttk.Button(form, text="Agendar", command=self.salvar_agendamento).grid(row=4, column=1, padx=6, pady=8, sticky="e")
        ttk.Button(form, text="Enviar lembrete no WhatsApp", command=self.whatsapp_agenda).grid(row=4, column=2, padx=6, pady=8)
        self.agenda_tree = self.tree(self.agenda_tab, ["ID", "Cliente", "Telefone", "Serviço", "Barbeiro", "Data/Hora", "Status"])

    def montar_fila(self):
        form = ttk.LabelFrame(self.fila_tab, text="Entrada por ordem de chegada")
        form.pack(fill="x", padx=10, pady=8)
        self.fila_cliente = self.combo(form, "Cliente", 0)
        self.fila_servico = self.combo(form, "Serviço", 1)
        self.fila_barbeiro = self.combo(form, "Barbeiro preferido", 2)
        ttk.Button(form, text="Entrar na fila", command=self.entrar_fila).grid(row=3, column=1, padx=6, pady=8, sticky="e")
        ttk.Button(form, text="Chamar próximo", command=self.chamar_proximo).grid(row=3, column=2, padx=6, pady=8)
        ttk.Button(form, text="Finalizar selecionado", command=self.finalizar_fila).grid(row=3, column=3, padx=6, pady=8)
        self.fila_tree = self.tree(self.fila_tab, ["Ordem", "ID", "Cliente", "Serviço", "Barbeiro", "Chegada", "Status"])

    def montar_config(self):
        serv = ttk.LabelFrame(self.config_tab, text="Cadastrar serviço")
        serv.pack(fill="x", padx=10, pady=8)
        self.serv_nome = self.campo(serv, "Nome", 0)
        self.serv_preco = self.campo(serv, "Preço", 1)
        self.serv_duracao = self.campo(serv, "Duração em minutos", 2)
        ttk.Button(serv, text="Salvar serviço", command=self.salvar_servico).grid(row=3, column=1, sticky="e", padx=6, pady=8)
        barb = ttk.LabelFrame(self.config_tab, text="Cadastrar barbeiro")
        barb.pack(fill="x", padx=10, pady=8)
        self.barb_nome = self.campo(barb, "Nome", 0)
        ttk.Button(barb, text="Salvar barbeiro", command=self.salvar_barbeiro).grid(row=1, column=1, sticky="e", padx=6, pady=8)
        self.config_tree = self.tree(self.config_tab, ["Tipo", "ID", "Nome", "Preço", "Duração"])

    def combo(self, parent, label, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=6, pady=4)
        cb = ttk.Combobox(parent, width=32, state="readonly")
        cb.grid(row=row, column=1, sticky="ew", padx=6, pady=4)
        return cb

    def tree(self, parent, columns):
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True, padx=10, pady=8)
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=135)
        tree.pack(side="left", fill="both", expand=True)
        ttk.Scrollbar(frame, orient="vertical", command=tree.yview).pack(side="right", fill="y")
        return tree

    def validar_combo_id(self, cb):
        if not cb.get():
            raise ValueError("Selecione todos os campos obrigatórios")
        return int(cb.get().split(" - ", 1)[0])

    def salvar_cliente(self):
        if not self.cliente_nome.get() or not self.cliente_tel.get():
            messagebox.showwarning("Atenção", "Nome e telefone são obrigatórios")
            return
        self.db.add_cliente(self.cliente_nome.get(), self.cliente_tel.get(), self.cliente_obs.get())
        self.limpar(self.cliente_nome, self.cliente_tel, self.cliente_obs)
        self.atualizar_tudo()

    def salvar_servico(self):
        try:
            self.db.add_servico(self.serv_nome.get(), float(self.serv_preco.get()), int(self.serv_duracao.get()))
            self.limpar(self.serv_nome, self.serv_preco, self.serv_duracao)
            self.atualizar_tudo()
        except ValueError:
            messagebox.showerror("Erro", "Preço e duração precisam ser números")

    def salvar_barbeiro(self):
        if self.barb_nome.get():
            self.db.add_barbeiro(self.barb_nome.get())
            self.limpar(self.barb_nome)
            self.atualizar_tudo()

    def salvar_agendamento(self):
        try:
            datetime.strptime(self.ag_data.get(), "%Y-%m-%d %H:%M")
            self.db.executar(
                "INSERT INTO agendamentos(cliente_id, barbeiro_id, servico_id, data_hora, criado_em) VALUES(?,?,?,?,?)",
                (self.validar_combo_id(self.ag_cliente), self.validar_combo_id(self.ag_barbeiro), self.validar_combo_id(self.ag_servico), self.ag_data.get(), datetime.now().isoformat(timespec="minutes")),
            )
            self.atualizar_tudo()
        except ValueError as e:
            messagebox.showerror("Erro", str(e) or "Data inválida")

    def entrar_fila(self):
        try:
            barbeiro = self.validar_combo_id(self.fila_barbeiro) if self.fila_barbeiro.get() else None
            self.db.executar(
                "INSERT INTO fila(cliente_id, servico_id, barbeiro_id, chegada_em) VALUES(?,?,?,?)",
                (self.validar_combo_id(self.fila_cliente), self.validar_combo_id(self.fila_servico), barbeiro, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            )
            self.atualizar_tudo()
        except ValueError as e:
            messagebox.showerror("Erro", str(e))

    def chamar_proximo(self):
        row = self.db.rows("SELECT id FROM fila WHERE status='Aguardando' ORDER BY chegada_em LIMIT 1")
        if not row:
            messagebox.showinfo("Fila", "Ninguém aguardando")
            return
        self.db.executar("UPDATE fila SET status='Em atendimento' WHERE id=?", (row[0]["id"],))
        self.atualizar_tudo()

    def finalizar_fila(self):
        sel = self.fila_tree.selection()
        if not sel:
            messagebox.showwarning("Atenção", "Selecione uma pessoa na fila")
            return
        fila_id = self.fila_tree.item(sel[0])["values"][1]
        self.db.executar("UPDATE fila SET status='Finalizado' WHERE id=?", (fila_id,))
        self.atualizar_tudo()

    def whatsapp_agenda(self):
        sel = self.agenda_tree.selection()
        if not sel:
            messagebox.showwarning("Atenção", "Selecione um agendamento")
            return
        _, cliente, telefone, servico, barbeiro, data_hora, _ = self.agenda_tree.item(sel[0])["values"]
        msg = f"Olá {cliente}! Confirmando seu horário na barbearia: {servico} com {barbeiro} em {data_hora}. Responda para confirmar."
        numero = "".join(ch for ch in str(telefone) if ch.isdigit())
        webbrowser.open(f"https://wa.me/{numero}?text={urllib.parse.quote(msg)}")

    def atualizar_tudo(self):
        clientes = self.db.rows("SELECT * FROM clientes ORDER BY nome")
        barbeiros = self.db.rows("SELECT * FROM barbeiros WHERE ativo=1 ORDER BY nome")
        servicos = self.db.rows("SELECT * FROM servicos ORDER BY nome")
        self.preencher_combo(self.ag_cliente, clientes, "nome")
        self.preencher_combo(self.fila_cliente, clientes, "nome")
        self.preencher_combo(self.ag_barbeiro, barbeiros, "nome")
        self.preencher_combo(self.fila_barbeiro, barbeiros, "nome")
        self.preencher_combo(self.ag_servico, servicos, "nome")
        self.preencher_combo(self.fila_servico, servicos, "nome")
        self.popular_tabelas()

    def preencher_combo(self, cb, rows, campo):
        cb["values"] = [f"{r['id']} - {r[campo]}" for r in rows]

    def popular_tabelas(self):
        self.set_rows(self.clientes_tree, self.db.rows("SELECT id, nome, telefone, observacoes FROM clientes ORDER BY id DESC"))
        agenda_sql = """
            SELECT a.id, c.nome cliente, c.telefone, s.nome servico, b.nome barbeiro, a.data_hora, a.status
            FROM agendamentos a JOIN clientes c ON c.id=a.cliente_id JOIN servicos s ON s.id=a.servico_id JOIN barbeiros b ON b.id=a.barbeiro_id
            ORDER BY a.data_hora DESC
        """
        fila_sql = """
            SELECT ROW_NUMBER() OVER (ORDER BY f.chegada_em) ordem, f.id, c.nome cliente, s.nome servico, COALESCE(b.nome, 'Livre') barbeiro, f.chegada_em, f.status
            FROM fila f JOIN clientes c ON c.id=f.cliente_id JOIN servicos s ON s.id=f.servico_id LEFT JOIN barbeiros b ON b.id=f.barbeiro_id
            ORDER BY f.status!='Aguardando', f.chegada_em
        """
        self.set_rows(self.agenda_tree, self.db.rows(agenda_sql))
        self.set_rows(self.fila_tree, self.db.rows(fila_sql))
        config = [("Serviço", r["id"], r["nome"], f"R$ {r['preco']:.2f}", f"{r['duracao_min']} min") for r in self.db.rows("SELECT * FROM servicos")] + [("Barbeiro", r["id"], r["nome"], "-", "-") for r in self.db.rows("SELECT * FROM barbeiros")]
        self.set_rows(self.config_tree, config)
        admin = [("Agenda", *r[1:]) for r in self.db.rows(agenda_sql)] + [("Fila", r[2], r[3], r[4], r[5], r[6]) for r in self.db.rows(fila_sql)]
        self.set_rows(self.admin_tree, admin)
        faturamento = self.db.rows("SELECT COALESCE(SUM(s.preco),0) total FROM fila f JOIN servicos s ON s.id=f.servico_id WHERE f.status='Finalizado'")[0]["total"]
        aguardando = self.db.rows("SELECT COUNT(*) qtd FROM fila WHERE status='Aguardando'")[0]["qtd"]
        agendados = self.db.rows("SELECT COUNT(*) qtd FROM agendamentos WHERE status='Agendado'")[0]["qtd"]
        self.cards.set(f"Admin: {agendados} agendados | {aguardando} na fila | faturamento finalizado R$ {faturamento:.2f}")

    def set_rows(self, tree, rows):
        tree.delete(*tree.get_children())
        for row in rows:
            tree.insert("", "end", values=tuple(row))

    def limpar(self, *entries):
        for entry in entries:
            entry.delete(0, "end")


if __name__ == "__main__":
    App().mainloop()
