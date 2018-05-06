$(document).ready(function() {
	$('select').material_select();
	$('form').submit(function(e) {
		Materialize.toast('Sent', 4000);
	});
});
