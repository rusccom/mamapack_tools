async function loginMarini(creds) {
  const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
  setInputValue("customerName", creds.company);
  await sleep(1300);
  setInputValue("userName", creds.employee);
  setInputValue("password", creds.password);
  checkInput("LoginConfirmation");
  await sleep(300);
  const submit = findSubmitButton();
  submit.click();
  return currentLoginState(Boolean(submit));
}

function setInputValue(name, value) {
  const input = findInput(name);
  const setter = Object.getOwnPropertyDescriptor(
    HTMLInputElement.prototype,
    "value",
  ).set;
  setter.call(input, value);
  input.dispatchEvent(new InputEvent("input", inputEventData(value)));
  input.dispatchEvent(new Event("change", { bubbles: true }));
  input.dispatchEvent(new Event("blur", { bubbles: true }));
}

function checkInput(name) {
  const input = findInput(name);
  if (!input.checked) input.click();
  input.dispatchEvent(new Event("change", { bubbles: true }));
}

function findInput(name) {
  const selector = `input[name="${name}"]`;
  const input = document.querySelector(selector);
  if (!input) throw new Error(`Missing input: ${name}`);
  return input;
}

function inputEventData(value) {
  return { bubbles: true, inputType: "insertText", data: value };
}

function findSubmitButton() {
  const buttons = [...document.querySelectorAll("form button")];
  const submit = buttons.find(isLogOnButton) || buttons[0];
  if (!submit) throw new Error("Missing login submit button");
  return submit;
}

function isLogOnButton(button) {
  return button.innerText.trim().includes("Log On");
}

function currentLoginState(clicked) {
  return {
    clicked,
    url: location.href,
    fields: collectLoginFields(),
  };
}

function collectLoginFields() {
  return [...document.querySelectorAll("input")].map(input => ({
    name: input.name,
    type: input.type,
    filled: input.type === "password" ? Boolean(input.value) : undefined,
    checked: input.checked,
  }));
}
