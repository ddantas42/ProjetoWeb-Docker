window.onload = async function onload() {UpdateMap()}


async function AddMarker(map, videos)
{
    for (const video of videos) {
        var marker = L.marker([video.latitude, video.longitude]).addTo(map);
        console.log('marker on:', video.latitude, video.longitude);
		const link = `<a href="#" onclick="openVideoWindow(${video.id}); return false;">${video.title}</a>`;
        marker.bindPopup(link);
    }
}

function openVideoWindow(videoId) {
    const url = `/watch/${videoId}`;
    const windowFeatures = "width=800,height=600,resizable,scrollbars";
    window.open(url, "_blank", windowFeatures);
}


// Initialize the map
const map = L.map('map').setView([0, 0], 2) // Default view (lat, lng, zoom)

async function UpdateMap(search = '')
{

	// Add OpenStreetMap tiles
	L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom: 18,}).addTo(map)

	// clear markers
	map.eachLayer(function (layer)
	{
		if (layer instanceof L.Marker)
			map.removeLayer(layer);
	});

	try
	{
		const response = await fetch('/api/videos', {
			credentials: 'same-origin'
		})
		if (!response.ok)
			throw new Error('Network response was not ok')

		const data = await response.json()
		console.log(data)

		var data2 = Object.values(data)

		if (search != '')
			data2 = data2.filter(video => video.title.toLowerCase().includes(search.toLowerCase()))

		AddMarker(map, data2)
	}
	catch (error)
	{
		console.error("erro:", error)
	}
}

async function SearchMap()
{
	var search = document.getElementById('searchInput').value
	UpdateMap(search)
}