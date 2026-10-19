const setIcon = (btn, name) => {
	const i = document.createElement("i");
	i.className = "ic";
	i.dataset.lucide = name;
	btn.replaceChildren(i);
	lucide.createIcons();
};
const root = document.documentElement;
const themeBtn = document.getElementById("theme");
const paint = () => setIcon(themeBtn, root.dataset.theme === "light" ? "moon" : "sun");
paint();
themeBtn.onclick = () => {
	const n = root.dataset.theme === "light" ? "dark" : "light";
	root.dataset.theme = n;
	try {
		localStorage.setItem("hop-theme", n);
	} catch (e) {}
	paint();
};

const copyBtn = document.getElementById("copy");
setIcon(copyBtn, "copy");
copyBtn.onclick = async () => {
	try {
		await navigator.clipboard.writeText(document.getElementById("cmd").textContent);
		setIcon(copyBtn, "check");
		setTimeout(() => setIcon(copyBtn, "copy"), 1400);
	} catch (e) {}
};

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
