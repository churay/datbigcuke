/**
 * @file setup.js
 * @author Joseph Ciurej
 * @date Spring 2014
 *
 * Container Module for Base Setup Logic for CS411 Project Pages
 *
 * @TODO
 */

/**
 * Main function for the 'setup.js' script file.
 */
function main()
{
	// Setup the Editable Fields //
	$.fn.editable.defaults.mode = "popup";
	$( ".editable-field" ).editable();

	// Setup the Deadline List Modules //
	$( ".deadline-notes" ).hide();
	$( ".deadline-entry" ).click( function() {
		$( this ).find( ".deadline-notes" ).slideToggle( "slow" );
	} );

	$( "#google_auth" ).click( function() {
		$.post("google-auth-request", function(url) {
			window.location.replace(url);
		});
	} );
}


$( document ).ready( main );

