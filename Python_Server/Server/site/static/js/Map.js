window.onload = async function onload() { UpdateMap() }

// Initialize the map
const map = L.map('map').setView([0, 0], 2) // Default view (lat, lng, zoom)

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 18 }).addTo(map)

const videoMarkers = L.layerGroup().addTo(map)
const sensorMarkers = L.layerGroup().addTo(map)

const sensorIcon = L.divIcon({
	className: 'sensor-marker-icon',
	html: '<span class="sensor-pin"></span>',
	iconSize: [24, 24],
	iconAnchor: [12, 12],
	popupAnchor: [0, -14]
})

function toNumber(value)
{
	const number = Number(value)
	return Number.isFinite(number) ? number : null
}

function formatCoordinate(value)
{
	const number = Number(value)
	return Number.isFinite(number) ? number.toFixed(6) : '--'
}

function formatValue(value, unit = '')
{
	if (value === undefined || value === null || value === '') {
		return '--'
	}
	return `${value}${unit}`
}

function pick(source, keys)
{
	for (const key of keys) {
		if (source && source[key] !== undefined && source[key] !== null && source[key] !== '') {
			return source[key]
		}
	}
	return undefined
}

function createPopupRow(label, value)
{
	const row = document.createElement('div')
	row.textContent = `${label}: ${value}`
	return row
}

function openVideoWindow(videoId)
{
	const url = `/watch/${videoId}`
	const windowFeatures = "width=800,height=600,resizable,scrollbars"
	window.open(url, "_blank", windowFeatures)
}

function AddMarker(videos, boundsPoints)
{
	for (const video of videos) {
		const latitude = toNumber(video.latitude)
		const longitude = toNumber(video.longitude)

		if (latitude === null || longitude === null) {
			console.warn('Video without valid coordinates:', video)
			continue
		}

		const marker = L.marker([latitude, longitude]).addTo(videoMarkers)
		const link = document.createElement('a')
		link.href = `/watch/${video.id}`
		link.textContent = video.title || `Video ${video.id}`
		link.addEventListener('click', function (event) {
			event.preventDefault()
			openVideoWindow(video.id)
		})
		marker.bindPopup(link)
		boundsPoints.push([latitude, longitude])
	}
}

async function AddSensorMarkers(boundsPoints)
{
	try {
		const response = await fetch('/api/iot/rest/state', {
			credentials: 'same-origin'
		})

		if (!response.ok) {
			throw new Error('Network response was not ok')
		}

		const data = await response.json()
		const weather = data.weather || {}
		const position = weather.position || {}

		if (position.error) {
			throw new Error(position.error)
		}

		const latitude = toNumber(pick(position, ['latitude', 'lat']))
		const longitude = toNumber(pick(position, ['longitude', 'lng', 'lon']))

		if (latitude === null || longitude === null) {
			console.warn('Sensor without valid coordinates:', position)
			return
		}

		const values = weather.values || {}
		const coordinates = `${formatCoordinate(latitude)}, ${formatCoordinate(longitude)}`
		const popup = document.createElement('div')
		popup.className = 'sensor-popup'

		const title = document.createElement('strong')
		title.textContent = 'Weather Sensor'
		popup.appendChild(title)
		popup.appendChild(createPopupRow('Coordinates', coordinates))
		popup.appendChild(createPopupRow('Temperature', formatValue(pick(values, ['temperature', 'temp']), ' C'))) // mudar aqui ou adicionar novos parametros json
		popup.appendChild(createPopupRow('Humidity', formatValue(pick(values, ['humidity']), '%')))

		const marker = L.marker([latitude, longitude], { icon: sensorIcon }).addTo(sensorMarkers)
		marker.bindPopup(popup)
		marker.bindTooltip(`Weather Sensor<br>${coordinates}`, {
			permanent: true,
			direction: 'top',
			offset: [0, -14],
			className: 'sensor-coordinate-tooltip'
		})

		boundsPoints.push([latitude, longitude])
	} catch (error) {
		console.error("erro sensor:", error)
	}
}

async function AddVideoMarkers(search, boundsPoints)
{
	try {
		const response = await fetch('/api/videos', {
			credentials: 'same-origin'
		})

		if (!response.ok) {
			throw new Error('Network response was not ok')
		}

		const data = await response.json()
		let videos = Object.values(data)

		if (search != '') {
			videos = videos.filter(video => (video.title || '').toLowerCase().includes(search.toLowerCase()))
		}

		AddMarker(videos, boundsPoints)
	} catch (error) {
		console.error("erro:", error)
	}
}

function FitMapToMarkers(boundsPoints)
{
	if (boundsPoints.length === 0) {
		map.setView([0, 0], 2)
		return
	}

	if (boundsPoints.length === 1) {
		map.setView(boundsPoints[0], 13)
		return
	}

	map.fitBounds(L.latLngBounds(boundsPoints), {
		padding: [40, 40],
		maxZoom: 13
	})
}

async function UpdateMap(search = '')
{
	videoMarkers.clearLayers()
	sensorMarkers.clearLayers()

	const boundsPoints = []

	await Promise.all([
		AddVideoMarkers(search, boundsPoints),
		AddSensorMarkers(boundsPoints)
	])

	FitMapToMarkers(boundsPoints)
}

async function SearchMap()
{
	const search = document.getElementById('searchInput').value
	UpdateMap(search)
}
