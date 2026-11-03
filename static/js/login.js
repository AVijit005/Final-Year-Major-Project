const inputs = document.querySelectorAll(".input");

function addcl(){
	let parent = this.parentNode.parentNode;
	parent.classList.add("focus");
}

function remcl(){
	let parent = this.parentNode.parentNode;
	if(this.value == ""){
		parent.classList.remove("focus");
	}
}

function checkInputs() {
	inputs.forEach(input => {
		let parent = input.parentNode.parentNode;
		if (input.value && input.value.trim() !== "") {
			parent.classList.add("focus");
		}
	});
}

inputs.forEach(input => {
	input.addEventListener("focus", addcl);
	input.addEventListener("blur", remcl);
	input.addEventListener("input", function() {
		let parent = this.parentNode.parentNode;
		if (this.value != "") {
			parent.classList.add("focus");
		}
	});
});

document.addEventListener("DOMContentLoaded", checkInputs);
window.addEventListener("load", checkInputs);
setTimeout(checkInputs, 100);
setTimeout(checkInputs, 500);
