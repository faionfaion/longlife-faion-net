import React, { useEffect, useState } from "react";
import Layout from "../components/layout";

// Subscription page. Two faces of the same URL:
//  - no ?t=  : the sign-up form (double opt-in; the API only mails a confirm link).
//  - ?t=...  : the manage panel a confirmed subscriber reaches from any email link -
//              newsletter types, topics they care about, and news links worth a look.
// It talks to the same-origin /api/ service, so no CORS and no keys in the client.

const API = "/api";

function useQuery() {
  const [q, setQ] = useState({});
  useEffect(() => {
    const p = new URLSearchParams(window.location.search);
    setQ(Object.fromEntries(p.entries()));
  }, []);
  return q;
}

function SubscribeForm() {
  const [email, setEmail] = useState("");
  const [hp, setHp] = useState("");
  const [weekly, setWeekly] = useState(true);
  const [each, setEach] = useState(false);
  const [state, setState] = useState("idle"); // idle | sending | sent | error

  const submit = async (e) => {
    e.preventDefault();
    setState("sending");
    try {
      const r = await fetch(`${API}/subscribe`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, hp, weekly, each_post: each }),
      });
      setState(r.ok ? "sent" : "error");
    } catch {
      setState("error");
    }
  };

  if (state === "sent") {
    return (
      <p className="sub-note">
        Майже готово. Я надіслала лист на <strong>{email}</strong> - відкрий посилання
        в ньому, щоб підтвердити підписку. Якщо листа немає за кілька хвилин, перевір
        теку зі спамом.
      </p>
    );
  }

  return (
    <form className="sub-form" onSubmit={submit}>
      <label className="sub-field">
        <span>Твоя пошта</span>
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="ty@example.com"
        />
      </label>

      {/* honeypot: hidden from people, tempting to bots */}
      <input
        type="text"
        name="website"
        tabIndex="-1"
        autoComplete="off"
        value={hp}
        onChange={(e) => setHp(e.target.value)}
        style={{ position: "absolute", left: "-9999px" }}
        aria-hidden="true"
      />

      <fieldset className="sub-kinds">
        <legend>Що надсилати</legend>
        <label>
          <input type="checkbox" checked={weekly} onChange={(e) => setWeekly(e.target.checked)} />
          Тижневий дайджест (неділя)
        </label>
        <label>
          <input type="checkbox" checked={each} onChange={(e) => setEach(e.target.checked)} />
          Кожен допис
        </label>
      </fieldset>

      <button type="submit" disabled={state === "sending"}>
        {state === "sending" ? "Надсилаю..." : "Підписатися"}
      </button>
      {state === "error" && (
        <p className="sub-note sub-err">Щось пішло не так. Спробуй ще раз трохи згодом.</p>
      )}
      <p className="sub-fine">
        Подвійне підтвердження: доки не клікнеш посилання в листі, адреса в список не
        потрапляє. Відписатися можна будь-коли одним кліком.
      </p>
    </form>
  );
}

function ManagePanel({ token }) {
  const [prefs, setPrefs] = useState(null);
  const [saved, setSaved] = useState(false);
  const [topic, setTopic] = useState("");
  const [topicDone, setTopicDone] = useState(false);
  const [url, setUrl] = useState("");
  const [note, setNote] = useState("");
  const [newsDone, setNewsDone] = useState(false);

  useEffect(() => {
    fetch(`${API}/prefs?t=${encodeURIComponent(token)}`)
      .then((r) => (r.ok ? r.json() : { weekly: true, each_post: false }))
      .then(setPrefs)
      .catch(() => setPrefs({ weekly: true, each_post: false }));
  }, [token]);

  const savePrefs = async (next) => {
    setPrefs(next);
    setSaved(false);
    await fetch(`${API}/prefs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ t: token, weekly: next.weekly, each_post: next.each_post }),
    });
    setSaved(true);
  };

  const sendTopic = async (e) => {
    e.preventDefault();
    if (!topic.trim()) return;
    await fetch(`${API}/topics`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ t: token, text: topic }),
    });
    setTopic("");
    setTopicDone(true);
  };

  const sendNews = async (e) => {
    e.preventDefault();
    if (!url.trim()) return;
    await fetch(`${API}/news`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ t: token, url, note }),
    });
    setUrl("");
    setNote("");
    setNewsDone(true);
  };

  if (!prefs) return <p className="sub-note">Завантажую...</p>;

  return (
    <div className="sub-manage">
      <h2>Типи листів</h2>
      <fieldset className="sub-kinds">
        <label>
          <input
            type="checkbox"
            checked={prefs.weekly}
            onChange={(e) => savePrefs({ ...prefs, weekly: e.target.checked })}
          />
          Тижневий дайджест (неділя)
        </label>
        <label>
          <input
            type="checkbox"
            checked={prefs.each_post}
            onChange={(e) => savePrefs({ ...prefs, each_post: e.target.checked })}
          />
          Кожен допис
        </label>
      </fieldset>
      {saved && <p className="sub-note">Збережено.</p>}

      <h2>Теми, які тобі цікаві</h2>
      <p className="sub-fine">Напиши, про що хотіла б почитати. Я читаю всі побажання.</p>
      <form className="sub-inline" onSubmit={sendTopic}>
        <input
          type="text"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="напр. чи працює магній для сну"
        />
        <button type="submit">Надіслати</button>
      </form>
      {topicDone && <p className="sub-note">Дякую, записала.</p>}

      <h2>Новина, варта уваги</h2>
      <p className="sub-fine">Побачила щось цікаве про здоровʼя? Кинь посилання.</p>
      <form className="sub-inline sub-news" onSubmit={sendNews}>
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://..."
        />
        <input
          type="text"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="кілька слів, чому це цікаво (необовʼязково)"
        />
        <button type="submit">Надіслати</button>
      </form>
      {newsDone && <p className="sub-note">Дякую, гляну.</p>}

      <p className="sub-fine">
        <a href={`${API}/unsubscribe?t=${encodeURIComponent(token)}`}>Відписатися</a>
      </p>
    </div>
  );
}

const SubscribePage = () => {
  const q = useQuery();
  const token = q.t;

  return (
    <Layout>
      <article className="article">
        <header className="article-header">
          <h1 className="article-title">Підписка</h1>
        </header>
        <div className="article-body">
          {q.c === "1" && (
            <p className="sub-note">Підписку підтверджено. Нижче можна налаштувати листи.</p>
          )}
          {q.u === "1" && <p className="sub-note">Відписано. Шкода, що йдеш - повертайся.</p>}
          {q.e === "1" && (
            <p className="sub-note sub-err">Посилання недійсне або застаріле.</p>
          )}

          {token ? (
            <ManagePanel token={token} />
          ) : (
            <>
              <p>
                Доказово про здоровʼя, простою мовою - на пошту. Обери, що саме
                надсилати, і підтверди адресу за посиланням у листі.
              </p>
              <SubscribeForm />
            </>
          )}
        </div>
      </article>
    </Layout>
  );
};

export default SubscribePage;

export const Head = () => (
  <>
    <title>Підписка · Віта</title>
    <meta
      name="description"
      content="Підпишись на LongLife: тижневий дайджест або кожен допис. Доказово про здоровʼя, простою мовою."
    />
    <link rel="canonical" href="https://longlife.media/pidpyska/" />
    <html lang="uk" />
  </>
);
