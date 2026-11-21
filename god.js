// Same server that shows this page also keeps the live party list.
const API_URL = "/api/parties";

const FORM_LABEL = {
  fnaf: "FNAF",
  tadc: "TADC",
  flip: "Flipping"
};

const list = document.querySelector("#lobbies");
const status = document.querySelector("#status");
const picked = document.querySelector("#picked");
const pickedName = document.querySelector("#picked-name");
const pickedDetail = document.querySelector("#picked-detail");

let chosen = null;

function playerLine(lobby) {
  const people = lobby.players === 1 ? "1 player" : `${lobby.players} players`;
  const age = lobby.minutes === 1 ? "1 min" : `${lobby.minutes} min`;
  const world = lobby.world === 1 ? "Universe 1" : `Universe ${lobby.world}`;
  return `${world} · ${people} · ${age}`;
}

function render(lobbies) {
  list.replaceChildren();
  if (chosen && !lobbies.some((lobby) => lobby.id === chosen)) {
    chosen = null;
    picked.hidden = true;
  }
  if (!lobbies.length) {
    const empty = document.createElement("li");
    empty.className = "empty";
    empty.textContent = "No games are running. Press Play in Studio.";
    list.append(empty);
    return;
  }

  for (const lobby of lobbies) {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.className = `lobby ${lobby.form}`;
    button.setAttribute("aria-pressed", chosen === lobby.id ? "true" : "false");
    button.innerHTML = `
      <span class="row">
        <span class="code"></span>
        <span class="form"></span>
      </span>
      <span class="meta"></span>
      <p class="note"></p>
    `;
    button.querySelector(".code").textContent = lobby.id;
    button.querySelector(".form").textContent = FORM_LABEL[lobby.form] || lobby.form;
    button.querySelector(".meta").textContent = playerLine(lobby);
    button.querySelector(".note").textContent = lobby.note;
    button.addEventListener("click", () => select(lobby, button));
    item.append(button);
    list.append(item);
  }
}

function select(lobby, button) {
  chosen = lobby.id;
  for (const other of list.querySelectorAll(".lobby")) {
    other.setAttribute("aria-pressed", "false");
  }
  button.setAttribute("aria-pressed", "true");
  picked.hidden = false;
  pickedName.textContent = lobby.id;
  pickedDetail.textContent = `You are the boss in this lobby. Current universe: ${FORM_LABEL[lobby.form] || lobby.form}. ${playerLine(lobby)}.`;
}

async function load() {
  try {
    const response = await fetch(API_URL, { cache: "no-store" });
    if (!response.ok) throw new Error(String(response.status));
    const lobbies = await response.json();
    if (!lobbies.length) {
      status.textContent = "Connected. No parties yet.";
    } else if (lobbies.length === 1) {
      status.textContent = "1 game alive";
    } else {
      status.textContent = `${lobbies.length} games alive`;
    }
    render(lobbies);
  } catch (error) {
    status.textContent = "The party server did not answer.";
    render([]);
  }
}

load();
setInterval(load, 4000);
