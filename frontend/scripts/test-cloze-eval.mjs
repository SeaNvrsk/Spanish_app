import { strict as assert } from "node:assert";
import { test } from "node:test";
import { isClozeCorrect, isTranslateCorrect } from "../src/answerMatch.js";

function cloze(template, answer) {
  return { template, answer, sentence: template.replace("___", answer) };
}

test("cloze accepts the blank plus words from the same sentence", () => {
  const ex = cloze("Ayer yo ___ mucho.", "estudié");
  assert.equal(isClozeCorrect(ex, "estudié"), true);
  assert.equal(isClozeCorrect(ex, "estudie"), true);
  assert.equal(isClozeCorrect(ex, "estudié mucho"), true);
  assert.equal(isClozeCorrect(ex, "Ayer yo estudié mucho."), true);
  assert.equal(isClozeCorrect(ex, "Ayer yo estudié"), true);
  assert.equal(isClozeCorrect(ex, "yo estudié mucho"), true);
  assert.equal(isClozeCorrect(ex, "estudio"), false);
  assert.equal(isClozeCorrect(ex, "mucho"), false);
  assert.equal(isClozeCorrect(ex, "estudié tacos"), false);
  assert.equal(isClozeCorrect(ex, ""), false);
});

test("same matching works for other cloze shapes", () => {
  assert.equal(isClozeCorrect(cloze("Ayer ___ tacos.", "comí"), "comí tacos"), true);
  assert.equal(isClozeCorrect(cloze("Ayer ___ tacos.", "comí"), "Ayer comí tacos"), true);
  assert.equal(isClozeCorrect(cloze("Anoche ___ al cine.", "fui"), "fui al cine"), true);
  assert.equal(isClozeCorrect(cloze("¿Qué ___ ayer?", "hiciste"), "qué hiciste ayer"), true);
  assert.equal(isClozeCorrect(cloze("___ a estudiar.", "Voy"), "Voy a estudiar"), true);
  assert.equal(isClozeCorrect(cloze("___ a estudiar.", "Voy"), "voy a"), true);
  assert.equal(isClozeCorrect(cloze("Estoy ___ español.", "hablando"), "estoy hablando"), true);
  assert.equal(isClozeCorrect(cloze("Buenos ___.", "días"), "Buenos días"), true);
  assert.equal(isClozeCorrect(cloze("___ casa es grande.", "La"), "La casa"), true);
  assert.equal(isClozeCorrect(cloze("Yo ___ de México.", "soy"), "Yo soy de México"), true);
  assert.equal(isClozeCorrect(cloze("Me ___ los tacos.", "gustan"), "me gustan"), true);
  assert.equal(isClozeCorrect(cloze("¿Cómo te ___?", "llamas"), "te llamas"), true);
  assert.equal(isClozeCorrect(cloze("Ayer ___ tacos.", "comí"), "comí pizza"), false);
  assert.equal(isClozeCorrect(cloze("___ a estudiar.", "Voy"), "Vas a estudiar"), false);
});

test("translate accepts the word plus light surrounding Spanish", () => {
  const ex = { answer: "estudié", es: "estudié", accepted_answers: ["estudié"] };
  assert.equal(isTranslateCorrect(ex, "estudié"), true);
  assert.equal(isTranslateCorrect(ex, "estudie"), true);
  assert.equal(isTranslateCorrect(ex, "yo estudié"), true);
  assert.equal(isTranslateCorrect(ex, "estudio"), false);
  assert.equal(isTranslateCorrect({ answer: "el taco", es: "el taco" }, "taco"), false);
  assert.equal(isTranslateCorrect({ answer: "taco", es: "taco" }, "el taco"), true);
  assert.equal(isTranslateCorrect({ answer: "Buenos días", es: "Buenos días" }, "buenos dias"), true);
});
