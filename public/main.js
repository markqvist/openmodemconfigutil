jQuery(document).ready(function() {
	init_elements();
	init_gfx();
	update_ports();
})

function update_ports() {
	jQuery.getJSON("/getports", function(data) {
		jQuery("#serialports").empty();
		jQuery.each(data, function(key, val) {
			jQuery("#serialports").append("<option value=\""+val+"\">"+val+"</option>")
			console.log(val);
		});
	});
}

function request_disconnect() {
	jQuery.getJSON("/disconnect", function(data) {
		console.log("Exiting...");
	});
}

function request_connection() {
	jQuery("#connectbutton").addClass("disabled");
	jQuery("#ind_connecting").addClass("active");
	port = jQuery("#serialports").val();
	baud = jQuery("#connectbaudrate").val()
	jQuery.getJSON("/connect?port="+port+"&baud="+baud, function(data) {
		console.log(data);
		if (data["response"] == "ok") {
			console.log("Serial port open");
			document.connection_state = true;
			setTimeout(request_config, 250);
		} else {
			console.log("Could not connect");
			document.connection_state = false;
			alert("Could not connect to the specified serial port. Please make sure the correct serial port is selected.");
			request_disconnect()
		}
	});
}

function request_config() {
	console.log("Requesting config...");
	$.ajax({
	  dataType: "json",
	  url: "/getconfig",
	  timeout: 500,
	  success: function(data) {
			if (data["response"] == "ok") {
				console.log("Connected!");
				jQuery("#disconnectbutton").show();
				jQuery("#connectbutton").hide();
				jQuery("#serialports").addClass("disabled");
				jQuery("#connectbaudrate").addClass("disabled");
				jQuery("#ind_connecting").removeClass("active");
				jQuery("#ind_disconnected").hide();
				jQuery("#ind_connected").show();
				jQuery("#configutil").accordion("open", 1);
				setInterval(function() {
					askForPeakData();
				}, 250);
			} else {
				console.log("Invalid response on config request");
				alert("Could not get configuration from selected device. Please make sure the correct serial port is selected.");
				request_disconnect();
			}
		},
	  error: function(jqXHR, status, error) {
	  	console.log("Request timed out");
	  	alert("Could not get configuration from selected device. Please make sure the correct serial port is selected.");
	  	request_disconnect();
	  }
	});
}

function init_elements() {
	document.connection_state = false;

	jQuery("#ind_connected").hide();
	jQuery("#disconnectbutton").hide();

	jQuery('.ui.accordion').accordion();
	jQuery('.ui.dropdown').dropdown();
	jQuery('.ui.checkbox').checkbox()

	jQuery('#p-selection').range({
		min: 0,
		max: 255,
		start: 128
	});

	jQuery('#led-selection').range({
		min: 0,
		max: 255,
		start: 0
	});

	jQuery('#ingain-selection').range({
		min: 0,
		max: 255,
		start: 0
	});

	jQuery('#outgain-selection').range({
		min: 0,
		max: 255,
		start: 0
	});

	jQuery("#connectbutton").click(function() {
		request_connection();
	});

	jQuery("#disconnectbutton").click(function() {
		request_disconnect();
	});
}

var graph_height = 0;
function init_gfx() {
	graph_height = 100;
	starty = graph_height-3;
	document.ingraph = Raphael(document.getElementById("inputgraph"), 519, 100);
}

function askForPeakData() {
	jQuery.getJSON("/getpeak", function(data) {
		if (data["response"] == "ok") {
			console.log(data);
			if (data["decode"] == true) {
				udpateInputGraph(1024);
				console.log("DECODE");
			} else {
				udpateInputGraph(parseInt(data["peak"]));
			}
		}
	})
}

function normalize(sample) {
	var factor = 255/graph_height;
	var res = ((sample*2)/factor)*0.98;
	//console.log(res);
	return res;
}

var in_samples_max = 103;
var in_samples = [];
var starty;
var t = 5;
var peak_threshold = 96;
var sw = t-2;
var ofs = 4;

function udpateInputGraph(peakval) {
	in_samples.push(peakval);
	if (in_samples.length > in_samples_max) {
		in_samples.shift();
	}
	document.ingraph.clear();

	for (i = 0; i < in_samples.length; i++) {
		var sample = normalize(in_samples[i]);
		var line = document.ingraph.path("M"+(i*t+ofs)+" "+starty+"V"+(starty-sample));
		if (in_samples[i] >= peak_threshold) {
			if (in_samples[i] >= 1024) {
				line.attr({stroke: "#00c", "stroke-width": sw});
			} else {
				line.attr({stroke: "#c00", "stroke-width": sw});
			} 
		} else {
			line.attr({stroke: "#0c0", "stroke-width": sw});
		}
	}
}