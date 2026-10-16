const $ = (s) => document.querySelector(s);
const ICONS = {
	plus: '<path d="M12 5v14M5 12h14"/>',
	search: '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>',
	ext: '<path d="M15 3h6v6M10 14 21 3M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
	edit: '<path d="M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/>',
	trash: '<path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6M10 11v6M14 11v6"/>',
	copy: '<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
	sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
	moon: '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z"/>',
	link: '<path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/>',
	radar: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4"/><path d="M12 12 19 5"/>',
	x: '<path d="M18 6 6 18M6 6l12 12"/>',
	chev: '<path d="m6 9 6 6 6-6"/>',
};
const ic = (n) => {
	const s = document.createElement("span");
	s.className = "ic";
	s.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' + ICONS[n] + "</svg>";
	return s;
};
function el(t, a = {}, ...c) {
	const e = document.createElement(t);
	for (const [k, v] of Object.entries(a)) {
		if (v === false || v == null) continue;
		if (k === "class") e.className = v;
		else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
		else e.setAttribute(k, v);
	}
	c.flat().forEach((x) => x != null && e.append(x));
	return e;
}
const api = async (m, u, b) => {
	try {
		const r = await fetch(u, { method: m, headers: { "Content-Type": "application/json" }, body: b ? JSON.stringify(b) : undefined });
		return await r.json();
	} catch (e) {
		return { error: "Could not reach the server" };
	}
};
function toast(msg, type = "ok") {
	const t = el("div", { class: "toast " + type }, msg);
	$("#toasts").append(t);
	setTimeout(() => t.classList.add("out"), 2800);
	setTimeout(() => t.remove(), 3200);
}
const copy = async (txt, label) => {
	try {
		await navigator.clipboard.writeText(txt);
		toast(label || "Copied");
	} catch (e) {
		toast("Copy failed", "er");
	}
};
const SVC = { 21: "FTP", 22: "SSH", 25: "SMTP", 53: "DNS", 80: "HTTP", 110: "POP3", 143: "IMAP", 443: "HTTPS", 445: "SMB", 1433: "MSSQL", 3306: "MySQL", 3389: "RDP", 5432: "PostgreSQL", 5672: "RabbitMQ", 5900: "VNC", 6379: "Redis", 9200: "Elasticsearch", 11211: "Memcached", 27017: "MongoDB" };

let S = { proxy_port: null, tld: "hop", app: "Hop" },
	R = {},
	SC = { running: false, done: 0, total: 0, results: [] },
	F = { q: "", kind: "all" },
	t0 = 0,
	editing = null;
const full = (n) => {
	n = (n || "").trim().toLowerCase();
	return n && !n.includes(".") ? n + "." + S.tld : n;
};
const short = (n) => {
	if (!n.endsWith("." + S.tld)) return n;
	const x = n.slice(0, -(S.tld.length + 1));
	return x.includes(".") ? n : x;
};
const urlFor = (n) => "http://" + n + (!S.proxy_port || S.proxy_port == 80 ? "" : ":" + S.proxy_port);

/* ---- theme ---- */
function paintTheme() {
	const l = document.documentElement.dataset.theme === "light";
	$("#theme").replaceChildren(ic(l ? "moon" : "sun"));
}
$("#theme").onclick = () => {
	const n = document.documentElement.dataset.theme === "light" ? "dark" : "light";
	document.documentElement.dataset.theme = n;
	try {
		localStorage.setItem("hop-theme", n);
	} catch (e) {}
	paintTheme();
};

/* ---- banners ---- */
function banner(id, title, text, pre) {
	unbanner(id);
	const b = el("div", { class: "banner wa", id: "bn-" + id }, el("div", { class: "bt" }, el("b", {}, title), el("span", { class: "m" }, text), pre ? el("pre", {}, pre) : null, pre ? el("div", { style: "margin-top:8px" }, el("button", { class: "btn sm", onclick: () => copy(pre, "Lines copied") }, ic("copy"), "Copy")) : null), el("button", { class: "btn sm icon ghost", title: "Dismiss", onclick: () => b.remove() }, ic("x")));
	$("#banners").append(b);
}
const unbanner = (id) => {
	const b = $("#bn-" + id);
	b && b.remove();
};

/* ---- status ---- */
const pill = (k, t) => el("span", { class: "pill " + k }, el("i", { class: "dot" }), t);
async function loadStatus() {
	const d = await api("GET", "/api/status");
	if (d.error) return;
	S = d;
	$("#pills").replaceChildren(pill(S.proxy_port ? "ok" : "er", "Proxy :" + (S.proxy_port || "off")), pill(S.admin ? "ok" : "wa", S.admin ? "Administrator" : "Not administrator"), S.local_ip ? el("button", { class: "pill", title: "Copy IP address", onclick: () => copy(S.local_ip, "IP copied") }, ic("copy"), S.local_ip) : null);
	if (!S.admin) banner("admin", "Running without administrator/root rights", "The hosts file cannot be written" + (S.proxy_port != 80 ? " and the proxy is on port " + S.proxy_port + " instead of 80" : "") + ". *.localhost names do not need a hosts entry; for any other name, restart the app as administrator.");
	else unbanner("admin");
}

/* ---- routes ---- */
async function loadRoutes() {
	const d = await api("GET", "/api/routes");
	if (d.error) return;
	R = d;
	renderRoutes();
	renderScan();
}
function renderRoutes() {
	const g = $("#routes"),
		names = Object.keys(R).sort((a, b) => !!R[b].builtin - !!R[a].builtin || a.localeCompare(b));
	$("#rcount").textContent = names.length;
	g.replaceChildren();
	if (!names.length) {
		g.append(el("div", { class: "empty" }, ic("link"), el("b", {}, "No routes yet"), el("span", {}, 'Scan for ports and click "Name it", or add a new route above.')));
		return;
	}
	names.forEach((n) => {
		const r = R[n],
			u = urlFor(n);
		g.append(
			el(
				"div",
				{ class: "route" },
				el("div", { class: "r-top" }, el("i", { class: "dot " + (r.up ? "ok" : "er"), title: r.up ? "Target is up" : "Target is not responding" }), el("a", { class: "r-name", href: u, target: "_blank", rel: "noopener", title: u }, n)),
				el("div", { class: "r-target mono" }, r.host + ":" + r.port),
				el("div", { class: "r-foot" }, r.builtin ? el("span", { class: "tag map" }, "panel") : r.rewrite_host ? el("span", { class: "tag" }, "host rewritten") : el("span"), el("div", { class: "acts" }, el("a", { class: "btn sm icon", href: u, target: "_blank", rel: "noopener", title: "Open" }, ic("ext")), el("button", { class: "btn sm icon", title: "Copy address", onclick: () => copy(u) }, ic("copy")), r.builtin ? null : el("button", { class: "btn sm icon", title: "Edit", onclick: () => openDlg({ name: n, host: r.host, port: r.port, rewrite: r.rewrite_host, orig: n }) }, ic("edit")), r.builtin ? null : el("button", { class: "btn sm icon danger", title: "Delete", onclick: () => del(n) }, ic("trash")))),
			),
		);
	});
}
async function del(n) {
	if (!confirm("Delete the route " + n + "?")) return;
	const r = await api("DELETE", "/api/routes/" + n);
	afterSave(r, null);
	loadRoutes();
}
function afterSave(r, name) {
	if (r.error) return toast(r.error, "er");
	if (r.hosts_ok === false) {
		banner("hosts", "Could not update the hosts file", "The route was saved, but you need to add these lines to the hosts file manually for the name to resolve:", (r.lines || []).join("\n"));
		toast("Saved, but the hosts file was not updated", "wa");
	} else {
		unbanner("hosts");
		toast(name ? "Saved: " + name : "Deleted");
	}
}

/* ---- dialog ---- */
const slug = (t, p) => {
	const s = (t || "")
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, "-")
		.replace(/^-+|-+$/g, "")
		.slice(0, 24);
	return s || "app" + p;
};
function prev() {
	const raw = $("#dn").value,
		sf = $("#sfx");
	sf.textContent = "." + S.tld;
	sf.style.display = raw.includes(".") ? "none" : "";
	const n = full(raw) || "name." + S.tld,
		p = $("#dp").value || "?",
		h = $("#dh").value.trim() || "127.0.0.1";
	$("#dprev").replaceChildren(el("b", {}, urlFor(n)), "  forwards to  http://" + h + ":" + p);
}
function openDlg(o = {}) {
	editing = o.orig || null;
	$("#dtitle").textContent = o.orig ? "Edit route" : "New route";
	$("#dn").value = short(o.name || "");
	$("#dh").value = o.host || "127.0.0.1";
	$("#dp").value = o.port || "";
	$("#dw").checked = !!o.rewrite;
	$("#derr").textContent = "";
	prev();
	$("#dlg").showModal();
	(o.name ? $("#dp") : $("#dn")).focus();
	if (!o.name) $("#dn").select();
}
["dn", "dh", "dp"].forEach((i) => $("#" + i).addEventListener("input", prev));
$("#dcancel").onclick = () => $("#dlg").close();
$("#addr").prepend(ic("plus"));
$("#addr").onclick = () => openDlg();
$("#dform").addEventListener("submit", async (e) => {
	e.preventDefault();
	const name = full($("#dn").value),
		host = $("#dh").value.trim() || "127.0.0.1",
		port = +$("#dp").value,
		err = (m) => ($("#derr").textContent = m);
	if (!/^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$/.test(name) || name === "localhost") return err("Invalid name. Example: cti");
	if (!(port >= 1 && port <= 65535)) return err("Port must be between 1 and 65535");
	let r = await api("POST", "/api/routes", { name, host, port, rewrite_host: $("#dw").checked });
	if (r.error) return err(r.error);
	if (editing && editing !== name) r = await api("DELETE", "/api/routes/" + editing);
	$("#dlg").close();
	afterSave(r, name);
	loadRoutes();
});

/* ---- scan ---- */
function mappedName(r) {
	for (const [n, x] of Object.entries(R)) {
		if (x.port === r.port && (x.host === r.host || (["127.0.0.1", "localhost"].includes(x.host) && r.host === "127.0.0.1"))) return n;
	}
	return null;
}
function passes(r) {
	const k = F.kind;
	if (k === "http" && r.kind !== "http") return false;
	if (k === "tcp" && r.kind === "http") return false;
	if (k === "local" && r.host !== "127.0.0.1") return false;
	if (k === "net" && r.host === "127.0.0.1") return false;
	const q = F.q.trim().toLowerCase();
	if (!q) return true;
	return [r.host, r.port, r.title, r.server, r.status, SVC[r.port] || "", mappedName(r) || ""].join(" ").toLowerCase().includes(q);
}
function renderScan() {
	const box = $("#results"),
		all = SC.results;
	box.replaceChildren();
	$("#ccount").textContent = all.length;
	const rows = all.filter(passes);
	const pct = SC.total ? Math.round((100 * SC.done) / SC.total) : 0;
	$("#pb").style.width = pct + "%";
	$("#fsum").textContent = SC.running ? `Scanning... ${pct}%` : "";
	$("#pt").textContent = SC.total ? (SC.running ? `Scanning... ${SC.done}/${SC.total} (${pct}%), ${Math.round((Date.now() - t0) / 1000)}s, ${all.length} open ports` : `Done: ${SC.total} addresses tried, ${all.length} open ports`) : "";
	const sb = $("#sb");
	sb.disabled = SC.running;
	sb.replaceChildren(ic("search"), el("span", {}, SC.running ? "Scanning..." : "Start scan"));
	if (!rows.length) {
		box.append(el("div", { class: "empty" }, ic("radar"), el("b", {}, SC.total ? (SC.running ? "No open ports found yet" : "No matching results") : "No scan has been run yet"), el("span", {}, SC.total ? "Try changing the filter or widening the range." : 'Pick a range and click "Start scan".')));
		return;
	}
	rows.forEach((r) => {
		const m = mappedName(r),
			http = r.kind === "http";
		box.append(
			el(
				"div",
				{ class: "row" + (r.is_self ? " self" : "") },
				el("div", {}, el("div", { class: "port mono" }, String(r.port)), el("div", { class: "host mono" }, r.host)),
				el("div", { style: "min-width:0" }, el("div", { class: "ttl" }, r.title || SVC[r.port] || (http ? "HTTP service" : "TCP service")), el("div", { class: "sub" }, [r.server, r.status].filter(Boolean).join(", ") || "-")),
				el("div", { class: "c-tags" }, r.is_self ? el("span", { class: "tag" }, S.app) : null, m ? el("a", { class: "tag map", href: urlFor(m), target: "_blank", rel: "noopener", title: "Open route" }, m) : null, SVC[r.port] && r.title ? el("span", { class: "tag" }, SVC[r.port]) : null, el("span", { class: "tag" + (http ? " http" : "") }, http ? "HTTP" : "TCP")),
				el("div", { class: "acts" }, http ? el("a", { class: "btn sm icon", href: `http://${r.host}:${r.port}`, target: "_blank", rel: "noopener", title: "Open" }, ic("ext")) : null, r.is_self ? null : el("button", { class: "btn sm", onclick: () => openDlg(m ? { name: m, host: r.host, port: r.port, rewrite: R[m].rewrite_host, orig: m } : { name: slug(r.title, r.port), host: r.host, port: r.port }) }, ic(m ? "edit" : "link"), m ? "Edit" : "Name it")),
			),
		);
	});
}
async function poll() {
	const d = await api("GET", "/api/scan");
	if (!d.error) SC = d;
	renderScan();
	if (SC.running) setTimeout(poll, 500);
}
$("#sb").onclick = async () => {
	const r = await api("POST", "/api/scan", { start: +$("#s").value || 1, end: +$("#e").value || 10000, subnet: $("#sub").checked });
	if (r.error) return toast(r.error, "er");
	t0 = Date.now();
	SC = { running: true, done: 0, total: 0, results: [] };
	renderScan();
	poll();
};
document.querySelectorAll("[data-r]").forEach(
	(b) =>
		(b.onclick = () => {
			const [a, z] = b.dataset.r.split("-");
			$("#s").value = a;
			$("#e").value = z;
		}),
);
document.querySelectorAll("[data-k]").forEach(
	(b) =>
		(b.onclick = () => {
			F.kind = b.dataset.k;
			document.querySelectorAll("[data-k]").forEach((x) => x.classList.toggle("on", x === b));
			renderScan();
		}),
);
$("#q").addEventListener("input", (e) => {
	F.q = e.target.value;
	renderScan();
});
addEventListener("keydown", (e) => {
	if (e.key === "/" && !/INPUT|TEXTAREA/.test(document.activeElement.tagName) && !$("#dlg").open) {
		e.preventDefault();
		setFold(false);
		$("#q").focus();
	}
});

function setFold(closed) {
	$("#scansec").classList.toggle("closed", closed);
	$("#fold").setAttribute("aria-expanded", String(!closed));
	try {
		localStorage.setItem("hop-fold", closed ? "1" : "0");
	} catch (e) {}
}
$("#fold").onclick = () => setFold(!$("#scansec").classList.contains("closed"));
{
	const c = ic("chev");
	c.classList.add("chev");
	$("#fold").prepend(c);
}
try {
	setFold(localStorage.getItem("hop-fold") === "1");
} catch (e) {}
paintTheme();
renderScan();
(async () => {
	await loadStatus();
	await loadRoutes();
	poll();
	setInterval(loadRoutes, 5000);
})();
