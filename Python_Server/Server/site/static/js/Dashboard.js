const tempHistory = [];

function setStatus(kind, ok, text) {
	const label = document.getElementById(`${kind}-status`);
	const dot = document.getElementById(`${kind}-status-dot`);
	label.textContent = text;
	dot.classList.toggle("ok", ok);
	dot.classList.toggle("error", !ok);
}

function formatValue(value, unit = "") {
	if (value === undefined || value === null || value === "") {
		return "--";
	}
	if (typeof value === "number") {
		return `${Number(value.toFixed(2))}${unit}`;
	}
	return `${value}${unit}`;
}

function pick(source, keys) {
	for (const key of keys) {
		if (source && source[key] !== undefined && source[key] !== null) {
			return source[key];
		}
	}
	return undefined;
}

function updateLastRefresh() {
	document.getElementById("last-refresh").textContent = `Last refresh: ${new Date().toLocaleTimeString()}`;
}

async function loadRestState() {
	try {
		const response = await fetch("/api/iot/rest/state");
		if (!response.ok) {
			throw new Error(`HTTP ${response.status}`);
		}
		const data = await response.json();
		const weather = data.weather?.values || {};
		const position = data.weather?.position || {};

		if (weather.error || position.error) {
			throw new Error(weather.error || position.error);
		}

		document.getElementById("rest-temperature").textContent = formatValue(pick(weather, ["temperature", "temp"]), " C");
		document.getElementById("rest-humidity").textContent = formatValue(pick(weather, ["humidity"]), "%");
		document.getElementById("rest-time").textContent = formatValue(pick(weather, ["time"]));
		document.getElementById("rest-position").textContent = `${formatValue(position.latitude)}, ${formatValue(position.longitude)}`;
		setStatus("rest", true, "REST connected");
		updateLastRefresh();
	} catch (error) {
		setStatus("rest", false, `REST error: ${error.message}`);
	}
}

function renderChart() {
	const chart = document.getElementById("temperature-chart");
	chart.innerHTML = "";
	const values = tempHistory.slice(-20);
	const numericValues = values.length ? values : [0];
	const min = Math.min(...numericValues);
	const max = Math.max(...numericValues);
	const range = Math.max(max - min, 1);

	for (const value of values) {
		const bar = document.createElement("span");
		const height = 10 + ((value - min) / range) * 90;
		bar.style.height = `${height}%`;
		bar.title = `${value} C`;
		chart.appendChild(bar);
	}
}

async function loadMqttState() {
	try {
		const response = await fetch("/api/iot/mqtt/latest");
		if (!response.ok) {
			throw new Error(`HTTP ${response.status}`);
		}
		const data = await response.json();
		const weather = data.topics?.["/weather"]?.value || {};
		const temperature = Number(pick(weather, ["temperature", "temp"]));

		document.getElementById("mqtt-broker").textContent = `Broker: ${data.broker?.host}:${data.broker?.port}`;
		document.getElementById("mqtt-temperature").textContent = formatValue(pick(weather, ["temperature", "temp"]), " C");
		document.getElementById("mqtt-humidity").textContent = formatValue(pick(weather, ["humidity"]), "%");
		document.getElementById("mqtt-time").textContent = formatValue(pick(weather, ["time"]));
		document.getElementById("mqtt-updated").textContent = data.last_update || "--";
		document.getElementById("mqtt-raw").textContent = JSON.stringify(data, null, 2);

		if (!Number.isNaN(temperature)) {
			const last = tempHistory[tempHistory.length - 1];
			if (last !== temperature) {
				tempHistory.push(temperature);
				renderChart();
			}
		}

		setStatus("mqtt", data.connected, data.connected ? "MQTT connected" : `MQTT waiting: ${data.last_error || "no message yet"}`);
	} catch (error) {
		setStatus("mqtt", false, `MQTT error: ${error.message}`);
	}
}

document.getElementById("refresh-rest").addEventListener("click", loadRestState);

loadRestState();
loadMqttState();
setInterval(loadRestState, 10000);
setInterval(loadMqttState, 2000);
