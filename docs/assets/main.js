const mk = (name) => {
	const i = document.createElement("i");
	i.className = "ic";
	i.dataset.lucide = name;
	return i;
};
const setIcon = (btn, name) => {
	btn.replaceChildren(mk(name));
	lucide.createIcons();
};

// install section
const inst = document.querySelector(".inst");
const hint = inst.querySelector("[data-os-hint]");
inst.querySelectorAll(".seg button").forEach((b) => {
	b.onclick = () => {
		const os = b.dataset.os;
		inst.querySelectorAll(".seg button").forEach((x) => {
			const on = x === b;
			x.classList.toggle("on", on);
			x.setAttribute("aria-selected", on);
		});
		inst.querySelectorAll("[data-unix]").forEach((el) => (el.textContent = el.dataset[os]));
		hint.innerHTML = os === "win" ? "Run as <span class='mono'>Administrator</span>" : "Run with <span class='mono'>sudo</span>";
	};
});
if (/win/i.test(navigator.platform || "")) inst.querySelector('[data-os="win"]').click();
inst.querySelectorAll(".cp").forEach((btn) => {
	setIcon(btn, "copy");
	btn.onclick = async () => {
		try {
			await navigator.clipboard.writeText(btn.parentElement.querySelector("code").textContent);
			setIcon(btn, "check");
			setTimeout(() => setIcon(btn, "copy"), 1400);
		} catch (e) {}
	};
});
lucide.createIcons();

// typing demo
const typed = document.getElementById("typed");
const names = ["cti.hop", "web.hop", "api.hop", "hop.hop"];
if (!matchMedia("(prefers-reduced-motion: reduce)").matches) {
	let i = 0;
	const run = async () => {
		for (;;) {
			const w = names[i++ % names.length];
			for (let k = 0; k <= w.length; k++) {
				typed.textContent = w.slice(0, k);
				await new Promise((r) => setTimeout(r, 110));
			}
			await new Promise((r) => setTimeout(r, 1600));
			for (let k = w.length; k >= 0; k--) {
				typed.textContent = w.slice(0, k);
				await new Promise((r) => setTimeout(r, 50));
			}
		}
	};
	run();
}
