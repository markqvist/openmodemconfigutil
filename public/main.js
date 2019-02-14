jQuery(document).ready(function() {
	init_elements();
	init_gfx();
})

function init_elements() {
	jQuery('.ui.accordion').accordion();
	jQuery('.ui.dropdown').dropdown();
	jQuery('.ui.checkbox').checkbox()

	$('#p-selection').range({
		min: 0,
		max: 255,
		start: 128
	});

	$('#led-selection').range({
		min: 0,
		max: 255,
		start: 192
	});

	$('#ingain-selection').range({
		min: 0,
		max: 255,
		start: 192
	});

	$('#outgain-selection').range({
		min: 0,
		max: 255,
		start: 192
	});
}

var graph_height = 0;
function init_gfx() {
	graph_height = 100;
	starty = graph_height-2;
	document.ingraph = Raphael(document.getElementById("inputgraph"), 519, 100);
	setInterval(function() {
		udpateInputGraph();
	}, 100);
}

function getInputPeak() {
	var rval = Math.random()*255+35;
	if (rval > 255) rval = 255;
	return rval;
}

function normalize(sample) {
	var factor = 255/graph_height;
	return (sample/factor)*0.98;
}

var in_samples_max = 103;
var in_samples = [];
var starty;
var t = 5;
var peak_threshold = 255;
var sw = t-2;
var ofs = 4;
function udpateInputGraph() {
	in_samples.push(getInputPeak());
	if (in_samples.length > in_samples_max) {
		in_samples.shift();
	}
	document.ingraph.clear();

	for (i = 0; i < in_samples.length; i++) {
		var sample = normalize(in_samples[i]);
		var line = document.ingraph.path("M"+(i*t+ofs)+" "+starty+"V"+(graph_height-sample));
		if (in_samples[i] >= peak_threshold) {
			line.attr({stroke: "#c00", "stroke-width": sw});
		} else {
			line.attr({stroke: "#0c0", "stroke-width": sw});
		}
	}
}