jQuery(document).ready(function() {
	init_elements();
	init_gfx();
	update_ports();
	update_volumes();
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

function update_volumes() {
	jQuery.getJSON("/getvolumes", function(data) {
		jQuery("#s_volumes").empty();
		jQuery("#s_volumes").append("<option value=\"none\">None</option>")
		jQuery.each(data, function(key, val) {
			jQuery("#s_volumes").append("<option value=\""+val+"\">"+val+"</option>")
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
			setTimeout(request_config, 600);
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
	  		console.log(data);
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
				jQuery(".savebutton").removeClass("disabled");
				update_fields_from_config(data["config"]);
				setInterval(function() {
					askForPeakData();
				}, 250);
				setTimeout(function() {
					document.connection_state = true;
				}, 500);
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

function update_slider_p() {
	var pval = parseInt(jQuery("#f_p").val());
	if (isNaN(pval)) pval = 255;
	if (pval > 255) pval = 255;
	if (pval < 0) pval = 0;
	jQuery("#p-selection").range("set value", pval);
	jQuery("#f_p").val(pval);
}

function update_slider_led(val) {
	if (isNaN(val)) val = 192;
	if (val < 0) val = 0;
	if (val > 255) val = 255;
	jQuery("#led-selection").range("set value", val);
}

function update_slider_ingain(val) {
	if (isNaN(val)) val = 63;
	if (val < 0) val = 0;
	if (val > 255) val = 255;
	jQuery("#ingain-selection").range("set value", val);
}

function update_slider_outgain(val) {
	if (isNaN(val)) val = 63;
	if (val < 0) val = 0;
	if (val > 255) val = 255;
	jQuery("#outgain-selection").range("set value", val);
}

function request_led_change(val) {
	if (document.connection_state) {
		if (isNaN(val)) val = 192;
		if (val < 0) val = 0;
		if (val > 255) val = 255;
		jQuery.getJSON("/setled?val="+val, function(data) {

		});
	}
}

function request_p_change(val) {	
	jQuery("#f_p").val(val);
	if (document.connection_state) {
		if (isNaN(val)) val = 192;
		if (val < 0) val = 0;
		if (val > 255) val = 255;
		console.log("Setting p to:");
		console.log(val);
		jQuery.getJSON("/setpersistence?val="+val, function(data) {

		});
	}
}

function request_preamble_change() {
	if (document.connection_state) {
		var val = parseInt(parseInt(jQuery("#f_preamble").val())/10);
		if (isNaN(val)) val = 150;
		if (val < 0) val = 0;
		if (val > 255) val = 255;
		console.log("Setting preamble to:");
		console.log(val);
		jQuery.getJSON("/setpreamble?val="+val, function(data) {

		});
		jQuery("#f_preamble").val(parseInt(val*10));
	}
}

function request_tail_change() {
	if (document.connection_state) {
		var val = parseInt(parseInt(jQuery("#f_tail").val())/10);
		if (isNaN(val)) val = 150;
		if (val < 0) val = 0;
		if (val > 255) val = 255;
		console.log("Setting tail to:");
		console.log(val);
		jQuery.getJSON("/settail?val="+val, function(data) {

		});
		jQuery("#f_tail").val(parseInt(val*10));
	}
}


function request_slottime_change() {
	if (document.connection_state) {
		var val = parseInt(parseInt(jQuery("#f_slottime").val())/10);
		if (isNaN(val)) val = 150;
		if (val < 0) val = 0;
		if (val > 255) val = 255;
		console.log("Setting slottime to:");
		console.log(val);
		jQuery.getJSON("/setslottime?val="+val, function(data) {

		});
		jQuery("#f_slottime").val(parseInt(val*10));
	}
}

function request_ingain_change(val) {
	if (document.connection_state) {
		if (isNaN(val)) val = 128;
		if (val < 0) val = 0;
		if (val > 255) val = 255;
		console.log("Setting input gain to:");
		console.log(val);
		jQuery.getJSON("/setingain?val="+val, function(data) {

		});
	}
}

function request_outgain_change(val) {
	if (document.connection_state) {
		if (isNaN(val)) val = 192;
		if (val < 0) val = 0;
		if (val > 255) val = 255;
		console.log("Setting output gain to:");
		console.log(val);
		jQuery.getJSON("/setoutgain?val="+val, function(data) {

		});
	}
}

function request_bluetoothmode_change() {
	if (document.connection_state) {
		var val = parseInt(jQuery("#s_bluetoothmode").val());
		if (isNaN(val)) val = 1;
		if (val < 0) val = 0;
		if (val > 2) val = 2;
		console.log("Setting bluetooth mode to:");
		console.log(val);
		jQuery.getJSON("/setbluetoothmode?val="+val, function(data) {

		});
	}
}

function request_gpsmode_change() {
	if (document.connection_state) {
		var val = parseInt(jQuery("#s_gpsmode").val());
		if (isNaN(val)) val = 1;
		if (val < 0) val = 0;
		if (val > 2) val = 2;
		console.log("Setting GPS mode to:");
		console.log(val);
		jQuery.getJSON("/setgpsmode?val="+val, function(data) {

		});
	}
}

function request_baudrate_change() {
	if (document.connection_state) {
		var val = parseInt(jQuery("#s_baudrate").val());
		if (isNaN(val)) val = 11;
		if (val < 1) val = 1;
		if (val > 12) val = 12;
		console.log("Setting baudrate to:");
		console.log(val);
		jQuery.getJSON("/setbaudrate?val="+val, function(data) {

		});
	}
}

function request_passall_change() {
	if (document.connection_state) {
		var val = jQuery("#c_passall").checkbox("is checked");
		val = val ? 1 : 0;
		console.log("Setting passall to:");
		console.log(val);
		jQuery.getJSON("/setpassall?val="+val, function(data) {	});
	}
}

function request_logtosd_change() {
	if (document.connection_state) {
		var val = jQuery("#c_logtosd").checkbox("is checked");
		val = val ? 1 : 0;
		console.log("Setting logtosd to:");
		console.log(val);
		jQuery.getJSON("/setlogtosd?val="+val, function(data) {	});
	}
}

function request_aes_change() {
	if (volume_ok) {
		var val = jQuery("#c_aes128").checkbox("is checked");
		if (val) {
			console.log("Enabling AES");
			jQuery.getJSON("/aesenable", function(data) { });
		} else {
			console.log("Disabling AES");
			jQuery.getJSON("/aesdisable", function(data) { });
		}
	} else {
		console.log("Not updating AES state, since no SD card is available")
	}
}

function request_generatekey() {
	if (volume_ok) {
		alert("A new AES-128 key will now be generated and installed onto the specified SD card. Please make a backup of this key somewhere secure, as there is no way to recover it if lost. Load this key to other modems that should be able to communicate with this one.");
		jQuery.getJSON("/generatekey", function(data) {
			if (data["response"] == "ok") {
				volume_changed();
			} else {
				alert("Could not generate new key. Make sure that you have write permission to the SD card.");
			}
		})
	}
}

function request_save_config() {
	if (document.connection_state) {
		$.ajax({
		  dataType: "json",
		  url: "/saveconfig",
		  timeout: 500,
		  success: function(data) {
				if (data["response"] == "ok") {
					console.log("Config saved");
					alert("Configuration was saved to the device");
					
				} else {
					console.log("Invalid response on config request");
					alert("Could not save configuration to selected device. Please make sure the correct serial port is selected.");
					request_disconnect();
				}
			},
		  error: function(jqXHR, status, error) {
		  	console.log("Request timed out");
		  	alert("Could not save configuration to selected device. Please make sure the correct serial port is selected.");
		  	request_disconnect();
		  }
		});
	}
}

function set_audio_sliders() {
	if (document.connection_state && !document.audioslidersset) {
		update_slider_ingain(parseInt(document.configdata["input_gain"]));
		update_slider_outgain(parseInt(document.configdata["output_gain"]));
		document.audioslidersset = true;
	}
}

function update_fields_from_config(configdata) {
	console.log("Config data:");
	console.log(configdata);
	document.configdata = configdata;

	jQuery("#f_preamble").val(parseInt(configdata["preamble"])*10);
	jQuery("#f_tail").val(parseInt(configdata["tail"])*10);
	jQuery("#f_slottime").val(parseInt(configdata["slottime"])*10);
	setTimeout(function() {
		jQuery("#f_p").val(parseInt(configdata["p"]));
		update_slider_p();
		update_slider_led(parseInt(configdata["led_intensity"]));
		jQuery("#s_gpsmode").dropdown("set selected", configdata["gps_mode"]);
		jQuery("#s_bluetoothmode").dropdown("set selected", configdata["bluetooth_mode"]);
		jQuery("#s_baudrate").dropdown("set selected", configdata["serial_baudrate"]);
		if (parseInt(configdata["passall"]) == 1) {
			jQuery("#c_passall").checkbox("check");
		} else {
			jQuery("#c_passall").checkbox("uncheck");
		}
		if (parseInt(configdata["log_packets"]) == 1) {
			jQuery("#c_logtosd").checkbox("check");
		} else {
			jQuery("#c_logtosd").checkbox("uncheck");
		}
		if (parseInt(configdata["modem_mode"]) == 1) { jQuery("#s_modem_mode").dropdown("set selected", "AFSK300");}
		if (parseInt(configdata["modem_mode"]) == 2) { jQuery("#s_modem_mode").dropdown("set selected", "AFSK1200");}
		if (parseInt(configdata["modem_mode"]) == 3) { jQuery("#s_modem_mode").dropdown("set selected", "AFSK2400");}
	}, 50);
}

function init_elements() {
	document.connection_state = false;
	document.audioslidersset = false;

	jQuery("#keyisready").hide();
	jQuery("#ind_connected").hide();
	jQuery("#disconnectbutton").hide();
	jQuery('#configutil').accordion({
		onOpen: function() {
			if (jQuery(this).hasClass("audiosection")) {
				setTimeout(set_audio_sliders, 50);
			}
		}
	});
	jQuery('.ui.dropdown').dropdown();
	
	jQuery("#s_gpsmode").dropdown("setting", "onChange", function() { request_gpsmode_change(); });
	jQuery("#s_bluetoothmode").dropdown("setting", "onChange", function() { request_bluetoothmode_change(); });
	jQuery("#s_baudrate").dropdown("setting", "onChange", function() { request_baudrate_change(); });
	jQuery("#s_volumes").dropdown("setting", "onChange", function() { volume_changed(); });

	jQuery('.ui.checkbox').checkbox()
	jQuery("#c_passall").checkbox("setting", "onChange", function() { request_passall_change(); });
	jQuery("#c_logtosd").checkbox("setting", "onChange", function() { request_logtosd_change(); });
	jQuery("#c_aes128").checkbox("setting", "onChange", function() { request_aes_change(); });

	jQuery('#p-selection').range({
		min: 0,
		max: 255,
		start: 128,
		onChange: function(val) {
			request_p_change(val);
		}
	});

	jQuery('#led-selection').range({
		min: 0,
		max: 255,
		start: 0,
		onChange: function(val) {
			request_led_change(val);
		}
	});

	jQuery('#ingain-selection').range({
		min: 0,
		max: 255,
		start: 0,
		onChange: function(val) {
			request_ingain_change(val);
		}
	});

	jQuery('#outgain-selection').range({
		min: 0,
		max: 255,
		start: 0,
		onChange: function(val) {
			request_outgain_change(val);
		}
	});

	jQuery(".savebutton").click(function() {
		request_save_config();
	})

	jQuery("#connectbutton").click(function() {
		request_connection();
	});

	jQuery("#disconnectbutton").click(function() {
		request_disconnect();
	});

	jQuery("#keygenerate .button").click(function() {
		request_generatekey();
	});

	jQuery("#keyfileinput").change(function(e) {
		if (e.target.files.length == 1) {
			var kf = e.target.files[0];
            var fr = new FileReader();
            fr.onload = function(e) {
              try {
                var stream = e.target.result;
                var keydata = btoa(stream);
                var url = "/loadkey?val="+encodeURIComponent(keydata);
                jQuery.getJSON(url, function(data) {
                	if (data["response"] == "ok") {
                		volume_changed();
                		alert("The key was successfully installed onto the SD card.");
                	} else {
                		alert("There was an error loading the specified key");
                	}
                });
              } catch (exception) {
                alert("An exception occurred while reading the specified key");
                console.log(exception);
              }
            }
            fr.readAsBinaryString(kf);
			/////////////////////////////////////
		} else {
			console.log("No or multiple files selected, not loading");
		}
	});

	jQuery("#f_p").on("blur", update_slider_p);

	jQuery("#f_preamble").on("blur", request_preamble_change);
	jQuery("#f_tail").on("blur", request_tail_change);
	jQuery("#f_slottime").on("blur", request_slottime_change);
}

var graph_height = 0;
function init_gfx() {
	graph_height = 100;
	starty = graph_height-3;
	document.ingraph = Raphael(document.getElementById("inputgraph"), 519, 100);
}

function askForPeakData() {
	if (document.connection_state) {
		jQuery.getJSON("/getpeak", function(data) {
			if (data["response"] == "ok") {
				if (data["decode"] == true) {
					udpateInputGraph(1024);
				} else {
					udpateInputGraph(parseInt(data["peak"]));
				}
			}
		});
	}
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
var peak_threshold = 122;
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

var volume_ok = false;
document.crypt_loading = false;
function volume_changed() {
	var volume = jQuery("#s_volumes").val();
	if (volume != "none") {
		document.crypt_loading = true;
		setTimeout(function() {
			if (document.crypt_loading) jQuery("#crypt_loader").addClass("active");
		}, 150);
		var url = "/volumeinit?path="+encodeURIComponent(volume)
		jQuery.getJSON(url, function(data) {
			console.log(data)
			document.crypt_loading = false;
			jQuery("#crypt_loader").removeClass("active");
			if (data["response"] == "ok") {
				if (data["aes_disabled"] == false && data["key_installed"] == true) {
					jQuery("#c_aes128").checkbox("check");
				} else {
					jQuery("#c_aes128").checkbox("uncheck");
				}
				if (data["key_installed"] == true) {
					jQuery("#keyisready").show();
					jQuery("#keyload").hide();
					jQuery("#keygenerate").hide();
					jQuery("#keyload .button").addClass("disabled");
					jQuery("#keygenerate .button").addClass("disabled");
					jQuery("#c_aes128").removeClass("disabled");
				} else {
					jQuery("#c_aes128").addClass("disabled");
					jQuery("#keyisready").hide();
					jQuery("#keyload .button").removeClass("disabled");
					jQuery("#keygenerate .button").removeClass("disabled");
					jQuery("#keyload").show();
					jQuery("#keygenerate").show();
				}
				volume_ok = true;
			} else {
				volume_ok = false;
				alert("The selected volume could not be initialised for use with OpenModem. Please make sure that you have write access to the volume, and that it is correctly formatted.");
			}
		});
	} else {
		volume_ok = false;
		jQuery("#keyisready").hide();
		jQuery("#keyload .button").addClass("disabled");
		jQuery("#keygenerate .button").addClass("disabled");
		jQuery("#keyload").show();
		jQuery("#keygenerate").show();
		jQuery("#c_aes128").checkbox("uncheck");
		jQuery("#c_aes128").addClass("disabled");
	}
}