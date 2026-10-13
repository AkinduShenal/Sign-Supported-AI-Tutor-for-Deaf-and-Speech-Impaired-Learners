import { useState, useCallback, useRef, useMemo, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { PanInfo } from "framer-motion";
import type { EvaluationResponse, QuestionAnswer } from "../types/nonImprovementSection";
import { evaluateSubmission } from "../api/nonImprovementSectionTutor";
import "./NonImprovementSection.css";

declare global {
  interface Window {
    googleTranslateElementInit: () => void;
    google: any;
  }
}

type Question = {
  id?: string;
  category?: string;
  prompt: string;
  equation: string;
  answers: number[];
  correct: number;
  visual?: "dots" | "bars" | "pie";
};

const questions: Question[] = [
  {
    prompt: "Add them together",
    equation: "1 + 1",
    answers: [2, 3, 1],
    correct: 2,
    visual: "dots",
  },
  {
    prompt: "Count the dots",
    equation: "2 + 1",
    answers: [4, 3, 2],
    correct: 3,
    visual: "dots",
  },
  {
    prompt: "What comes next?",
    equation: "3 + 1",
    answers: [5, 2, 4],
    correct: 4,
  },
  {
    prompt: "Add the bars",
    equation: "2 + 3",
    answers: [5, 6, 4],
    correct: 5,
    visual: "bars",
  },
  {
    prompt: "Take two away",
    equation: "7 − 2",
    answers: [4, 5, 6],
    correct: 5,
  },
  {
    prompt: "Double the number",
    equation: "3 + 3",
    answers: [5, 7, 6],
    correct: 6,
    visual: "dots",
  },
  {
    prompt: "Find the missing part",
    equation: "4 + ? = 7",
    answers: [2, 3, 4],
    correct: 3,
    visual: "pie",
  },
  {
    prompt: "Take three away",
    equation: "9 − 3",
    answers: [7, 5, 6],
    correct: 6,
  },
  {
    prompt: "Add one more",
    equation: "8 + 1",
    answers: [9, 8, 10],
    correct: 9,
    visual: "bars",
  },
  {
    prompt: "Final challenge",
    equation: "5 + 5",
    answers: [10, 9, 11],
    correct: 10,
    visual: "pie",
  },
];

function HomeIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M3.5 10.7 12 3.8l8.5 6.9v8.6a1.7 1.7 0 0 1-1.7 1.7H15v-6.1H9V21H5.2a1.7 1.7 0 0 1-1.7-1.7v-8.6Z" />
    </svg>
  );
}

function GearIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="m9.9 2.8.5-1.3h3.2l.5 1.3a2 2 0 0 0 2.5 1.1l1.3-.6 2.3 2.3-.6 1.3a2 2 0 0 0 1.1 2.5l1.3.5v3.2l-1.3.5a2 2 0 0 0-1.1 2.5l.6 1.3-2.3 2.3-1.3-.6a2 2 0 0 0-2.5 1.1l-.5 1.3h-3.2l-.5-1.3a2 2 0 0 0-2.5-1.1l-1.3.6-2.3-2.3.6-1.3a2 2 0 0 0-1.1-2.5L2 13.1V9.9l1.3-.5a2 2 0 0 0 1.1-2.5l-.6-1.3 2.3-2.3 1.3.6a2 2 0 0 0 2.5-1.1Zm2.1 12.9a4.2 4.2 0 1 0 0-8.4 4.2 4.2 0 0 0 0 8.4Z" />
    </svg>
  );
}

function SpeakerIcon({ muted }: { muted: boolean }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M4 9h4l5-4v14l-5-4H4V9Zm12.2-.7a5.2 5.2 0 0 1 0 7.4"
        className="speaker-wave"
      />
      {!muted && (
        <path
          d="M18.6 5.6a9 9 0 0 1 0 12.8"
          className="speaker-wave"
        />
      )}
      {muted && (
        <path
          d="m16.4 9 5 5m0-5-5 5"
          className="speaker-wave"
        />
      )}
    </svg>
  );
}

function Visual({ type }: { type?: Question["visual"] }) {
  if (type === "dots") {
    return (
      <div className="dot-visual" aria-hidden="true">
        <i />
        <i />
        <span>+</span>
        <i className="yellow" />
      </div>
    );
  }

  if (type === "bars") {
    return (
      <div className="bar-visual" aria-hidden="true">
        <i />
        <i />
        <i />
        <i />
      </div>
    );
  }

  if (type === "pie") {
    return (
      <svg
        className="pie-visual"
        viewBox="0 0 90 90"
        aria-hidden="true"
      >
        <circle cx="45" cy="45" r="36" />
        <path d="M45 45V9a36 36 0 0 1 36 36H45Z" />
        <path d="M45 45h36a36 36 0 0 1-36 36V45Z" />
      </svg>
    );
  }

  return null;
}

function StarMascot() {
  return (
    <svg
      className="star-mascot"
      viewBox="0 0 220 220"
      aria-label="Happy star"
    >
      <path
        className="star-shadow"
        d="m112 13 25 57 62 6-47 42 14 61-54-31-54 31 14-61-47-42 62-6 25-57Z"
      />
      <path
        className="star-body"
        d="m108 8 25 57 62 6-47 42 14 61-54-31-54 31 14-61-47-42 62-6 25-57Z"
      />
      <ellipse
        cx="83"
        cy="101"
        rx="7"
        ry="10"
        className="star-eye"
      />
      <ellipse
        cx="133"
        cy="101"
        rx="7"
        ry="10"
        className="star-eye"
      />
      <path d="M84 124q24 27 48 0" className="star-smile" />
      <circle cx="68" cy="119" r="9" className="star-cheek" />
      <circle cx="148" cy="119" r="9" className="star-cheek" />
    </svg>
  );
}

function Celebration({ onRestart, topic = "Non-Improvement Section" }: { onRestart: () => void; topic?: string }) {
  return (
    <main className="celebration" translate="no">
      <div className="firework firework-one" aria-hidden="true">
        {Array.from({ length: 12 }, (_, i) => (
          <i key={i} />
        ))}
      </div>
      <div className="firework firework-two" aria-hidden="true">
        {Array.from({ length: 10 }, (_, i) => (
          <i key={i} />
        ))}
      </div>
      <div className="confetti" aria-hidden="true">
        {Array.from({ length: 22 }, (_, i) => (
          <i key={i} />
        ))}
      </div>
      <div className="success-art">
        <div className="well-done" aria-label="Well done">
          <span>W</span>
          <span>e</span>
          <span>l</span>
          <span>l</span>
          <small> </small>
          <span>D</span>
          <span>o</span>
          <span>n</span>
          <span>e</span>
        </div>
        <StarMascot />
      </div>
      <p className="success-copy">
        You solved every challenge in the {topic}!
      </p>
      <button className="play-again" onClick={onRestart}>
        Continue
      </button>
    </main>
  );
}

interface NonImprovementSectionProps {
  topic?: string;
  onSwitchToTutor?: () => void;
  evaluationData: EvaluationResponse;
  onUpdateEvaluation?: (newData: EvaluationResponse) => void;
  onRestart: () => void;
}

export function NonImprovementSection({
  topic = "Non-Improvement Section",
  onSwitchToTutor,
  evaluationData,
  onUpdateEvaluation,
  onRestart,
}: NonImprovementSectionProps) {
  const [current, setCurrent] = useState(0);
  const [selected, setSelected] = useState<number | null>(null);
  const [completed, setCompleted] = useState(false);
  const [muted, setMuted] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [userAnswers, setUserAnswers] = useState<QuestionAnswer[]>([]);

  const audioCtxRef = useRef<AudioContext | null>(null);

  useEffect(() => {
    // Inject Google Translate script if not present
    if (!document.getElementById('google-translate-script')) {
      window.googleTranslateElementInit = () => {
        if (window.google && window.google.translate) {
          new window.google.translate.TranslateElement(
            { 
              pageLanguage: 'en', 
              includedLanguages: 'si,en',
              layout: window.google.translate.TranslateElement.InlineLayout.SIMPLE 
            },
            'google_translate_element'
          );
        }
      };

      const script = document.createElement('script');
      script.id = 'google-translate-script';
      script.src = '//translate.google.com/translate_a/element.js?cb=googleTranslateElementInit';
      script.async = true;
      document.body.appendChild(script);
    }
  }, []);

  const playSound = useCallback((soundType: 'click' | 'correct' | 'wrong' | 'celebrate') => {
    if (muted) return;
    try {
      if (!audioCtxRef.current) {
        const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
        if (AudioContextClass) {
          audioCtxRef.current = new AudioContextClass();
        }
      }
      const ctx = audioCtxRef.current;
      if (!ctx) return;
      if (ctx.state === 'suspended') {
        void ctx.resume();
      }

      const now = ctx.currentTime;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);

      if (soundType === 'click') {
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(440, now);
        gain.gain.setValueAtTime(0.12, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.08);
        osc.start(now);
        osc.stop(now + 0.08);
      } else if (soundType === 'correct') {
        osc.type = 'sine';
        osc.frequency.setValueAtTime(523.25, now); // C5
        osc.frequency.exponentialRampToValueAtTime(659.25, now + 0.1); // E5
        osc.frequency.exponentialRampToValueAtTime(783.99, now + 0.2); // G5
        gain.gain.setValueAtTime(0.2, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
        osc.start(now);
        osc.stop(now + 0.35);
      } else if (soundType === 'wrong') {
        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(220, now);
        osc.frequency.linearRampToValueAtTime(160, now + 0.2);
        gain.gain.setValueAtTime(0.15, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.25);
        osc.start(now);
        osc.stop(now + 0.25);
      } else if (soundType === 'celebrate') {
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(440, now);
        osc.frequency.setValueAtTime(554.37, now + 0.1);
        osc.frequency.setValueAtTime(659.25, now + 0.2);
        osc.frequency.setValueAtTime(880, now + 0.3);
        gain.gain.setValueAtTime(0.25, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.6);
        osc.start(now);
        osc.stop(now + 0.6);
      }
    } catch {
      // Audio not supported or blocked by browser policy
    }
  }, [muted]);

  const dynamicQuestions = useMemo<Question[]>(() => {
    if (!evaluationData.next_quiz || !evaluationData.next_quiz.questions.length) {
      return questions; // Fallback to default questions if none provided
    }
    return evaluationData.next_quiz.questions.map(q => {
      const correct = parseInt(q.correct_answer, 10);
      let answers: number[] = [correct];
      if (!isNaN(correct)) {
        while (answers.length < 3) {
          const offset = Math.floor(Math.random() * 5) + 1;
          const sign = Math.random() > 0.5 ? 1 : -1;
          const wrong = correct + (offset * sign);
          if (!answers.includes(wrong)) answers.push(wrong);
        }
        answers = answers.sort(() => Math.random() - 0.5);
      } else {
        // Fallback for non-integer answers
        answers = [0, 1, 2];
      }
      return {
        id: q.question_id,
        category: q.category,
        prompt: `Solve for x (${q.category.replace('_', ' ')})`,
        equation: q.question,
        answers,
        correct,
        visual: undefined
      };
    });
  }, [evaluationData]);

  const question = dynamicQuestions[current];
  const layers = current <= 3 ? 4 : current <= 7 ? 2 : current === 8 ? 1 : 0;

  const handleSelectAnswer = (answer: number) => {
    setSelected(answer);
    playSound('click');

    const recordedAnswer: QuestionAnswer = {
      question_id: question.id || `q_${current}`,
      question: question.equation,
      correct_answer: String(question.correct),
      user_answer: String(answer),
      category: (question.category || "single_variable") as any,
    };

    const newAnswers = [...userAnswers.slice(0, current), recordedAnswer];
    setUserAnswers(newAnswers);
  };

  const next = () => {
    if (selected === null) return;
    playSound('click');
        
    if (current === dynamicQuestions.length - 1) {
      handleQuizComplete(userAnswers);
    } else {
      setCurrent((value) => value + 1);
      setSelected(null);
    }
  };

  const handleQuizComplete = async (finalAnswers: QuestionAnswer[]) => {
    try {
      const response = await evaluateSubmission({
        user_id: evaluationData.user_id,
        questions: finalAnswers,
      });

      if (response.is_perfect || response.incorrect_count === 0) {
        setCompleted(true);
        playSound('celebrate');
      } else {
        if (onUpdateEvaluation) {
          onUpdateEvaluation(response);
          setCurrent(0);
          setSelected(null);
          setUserAnswers([]);
          setShowTutorial(true);
          setTutorialSlideIndex(0);
        }
      }
    } catch (err) {
      console.error(err);
    }
  };

  const [showTutorial, setShowTutorial] = useState(!!evaluationData.tutorial);
  const [tutorialSlideIndex, setTutorialSlideIndex] = useState(0);
  const tutorial = evaluationData.tutorial;
  
  const finishTutorial = () => {
    playSound('click');
    setShowTutorial(false);
  };

  return (
    <div className="app-shell">
      <div className="doodle-pattern" aria-hidden="true" />

      <button
        className="round-button home-button"
        aria-label="Go home and restart"
        onClick={onRestart}
      >
        <HomeIcon />
      </button>

      <button
        className="round-button settings-button"
        aria-label="Open settings"
        aria-expanded={settingsOpen}
        onClick={() => {
          playSound('click');
          setSettingsOpen((value) => !value);
        }}
      >
        <GearIcon />
      </button>

      <button
        className="round-button sound-button"
        aria-label={muted ? "Turn sound on" : "Mute sound"}
        aria-pressed={muted}
        onClick={() => {
          setMuted((value) => !value);
        }}
      >
        <SpeakerIcon muted={muted} />
      </button>

      {!completed && (
        <div 
          id="google_translate_element" 
          style={{ position: 'absolute', top: '20px', right: '140px', zIndex: 100 }}
        ></div>
      )}

      {settingsOpen && (
        <aside className="settings-panel">
          <strong>{topic}</strong>
          <button onClick={() => setMuted((value) => !value)}>
            Sound <span>{muted ? "Off" : "On"}</span>
          </button>
          <button onClick={onRestart}>Start over</button>
          {onSwitchToTutor && (
            <button className="switch-mode-btn" onClick={onSwitchToTutor}>
              Open Sign Tutor <span>→</span>
            </button>
          )}
        </aside>
      )}

      {completed ? (
        <Celebration onRestart={onRestart} topic={topic} />
      ) : showTutorial && tutorial ? (
        <main className="game" style={{ overflowY: 'auto', padding: '20px 0' }}>
          <section className="card-stage" style={{ minHeight: 'auto', margin: '20px auto' }}>
            <AnimatePresence mode="wait">
              <motion.article 
                key={tutorialSlideIndex}
                initial={{ opacity: 0, x: 50 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -50 }}
                transition={{ duration: 0.3 }}
                className="math-card" 
                style={{ 
                  textAlign: 'left', 
                  padding: '40px', 
                  borderLeft: '14px solid #4ade80', 
                  minHeight: '400px', 
                  display: 'flex', 
                  flexDirection: 'column', 
                  justifyContent: 'space-between' 
                }}
              >
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: tutorialSlideIndex === 0 ? 'center' : 'flex-start' }}>
                  {tutorialSlideIndex === 0 && (
                    <div style={{ 
                      flex: 1, 
                      display: 'flex', 
                      flexDirection: 'column', 
                      justifyContent: 'center', 
                      alignItems: 'center', 
                      textAlign: 'center', 
                      padding: '30px 20px',
                      margin: 'auto 0'
                    }}>
                      <h2 style={{ color: '#2c3e50', marginBottom: '20px', fontSize: '2.4rem', fontFamily: '"Nunito", sans-serif', fontWeight: 800 }}>
                        {tutorial.title}
                      </h2>
                      <div style={{ fontSize: '1.35rem', color: '#475569', lineHeight: '1.7', fontFamily: '"Nunito", sans-serif', maxWidth: '620px' }}>
                        {tutorial.introduction?.split('\n').map((line, i) => (
                          <p key={i} style={{ marginBottom: '14px' }}>{line}</p>
                        ))}
                      </div>
                    </div>
                  )}

                  {tutorialSlideIndex > 0 && tutorialSlideIndex <= (tutorial.steps?.length || 0) && (
                    <>
                      <h2 style={{ color: '#334155', marginBottom: '20px', fontSize: '1.8rem', fontFamily: '"Nunito", sans-serif' }}>
                        Step {tutorial.steps[tutorialSlideIndex - 1].step_number}
                      </h2>
                      <div style={{ marginBottom: '24px', display: 'flex', flexDirection: 'column', gap: '12px', fontFamily: '"Nunito", sans-serif', fontSize: '1.3rem', color: '#475569' }}>
                        {tutorial.steps[tutorialSlideIndex - 1].instruction?.split('\n').map((line, i) => (
                          <div key={i} style={{ display: 'flex', alignItems: 'flex-start' }}>
                            <span style={{ lineHeight: '1.5' }}>{line}</span>
                          </div>
                        ))}
                      </div>
                      <div style={{ 
                        backgroundColor: '#e6ebf1', 
                        borderRadius: '12px', 
                        padding: '24px', 
                        fontFamily: '"Nunito", monospace', 
                        fontSize: '1.25rem', 
                        color: '#1e293b',
                        boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.02)'
                      }}>
                        {tutorial.steps[tutorialSlideIndex - 1].example?.split('\n').map((line, i) => (
                          <div key={i} style={{ marginBottom: i === (tutorial.steps[tutorialSlideIndex - 1].example?.split('\n').length || 1) - 1 ? 0 : '10px' }}>
                            {line}
                          </div>
                        ))}
                      </div>
                    </>
                  )}

                  {tutorialSlideIndex === (tutorial.steps?.length || 0) + 1 && (
                    <div style={{ 
                      flex: 1, 
                      display: 'flex', 
                      flexDirection: 'column', 
                      justifyContent: 'center', 
                      alignItems: 'center', 
                      padding: '20px',
                      margin: 'auto 0'
                    }}>
                      {tutorial.tips && tutorial.tips.length > 0 && (
                        <div style={{ marginBottom: '32px', maxWidth: '600px', width: '100%' }}>
                          <h2 style={{ color: '#d97706', marginBottom: '20px', fontSize: '1.8rem', fontFamily: '"Nunito", sans-serif', textAlign: 'center' }}>💡 Top Tips</h2>
                          <ul style={{ paddingLeft: '24px', color: '#92400e', fontSize: '1.2rem', fontFamily: '"Nunito", sans-serif', lineHeight: '1.6' }}>
                            {tutorial.tips.map((tip, i) => <li key={i} style={{ marginBottom: '12px' }}>{tip}</li>)}
                          </ul>
                        </div>
                      )}
                      <div style={{ fontSize: '1.4rem', color: '#059669', textAlign: 'center', fontWeight: 'bold', fontFamily: '"Nunito", sans-serif', padding: '24px 32px', backgroundColor: '#ecfdf5', borderRadius: '16px', maxWidth: '600px', width: '100%' }}>
                        {tutorial.encouragement}
                      </div>
                    </div>
                  )}
                </div>

                <div style={{ 
                  display: 'flex', 
                  justifyContent: tutorialSlideIndex === 0 ? 'center' : 'space-between', 
                  alignItems: 'center',
                  marginTop: '32px' 
                }}>
                  {tutorialSlideIndex > 0 && (
                    <button
                      onClick={() => setTutorialSlideIndex(prev => Math.max(0, prev - 1))}
                      style={{
                        padding: '12px 24px',
                        borderRadius: '999px',
                        border: '2px solid #cbd5e1',
                        backgroundColor: 'transparent',
                        color: '#64748b',
                        fontSize: '1.1rem',
                        fontWeight: 'bold',
                        cursor: 'pointer'
                      }}
                    >
                      ⬅ Previous
                    </button>
                  )}

                  <button
                    className="next-button"
                    onClick={() => {
                      if (tutorialSlideIndex === (tutorial.steps?.length || 0) + 1) {
                        finishTutorial();
                      } else {
                        setTutorialSlideIndex(prev => prev + 1);
                      }
                    }}
                    style={{ padding: '12px 32px' }}
                  >
                    {tutorialSlideIndex === (tutorial.steps?.length || 0) + 1
                      ? "Let's Practice!"
                      : "Next"} <span>→</span>
                  </button>
                </div>
              </motion.article>
            </AnimatePresence>
          </section>
        </main>
      ) : (
        <main className="game">
          <div
            className="progress-badge"
            aria-label={`${topic}: Question ${current + 1} of ${dynamicQuestions.length}`}
          >
            <span>{current + 1}</span>
            <b>/</b>
            {dynamicQuestions.length}
          </div>

          <section className="card-stage" aria-live="polite">
            <div className="card-stack">
              {Array.from({ length: layers }, (_, index) => (
                <div
                  className={`stack-layer layer-${index + 1}`}
                  key={`${current}-layer-${index}`}
                  aria-hidden="true"
                />
              ))}
              <AnimatePresence mode="popLayout">
                <motion.article 
                  className="math-card" 
                  key={current}
                  initial={{ opacity: 0, x: 100, rotate: 5 }}
                  animate={{ opacity: 1, x: 0, rotate: 0 }}
                  exit={{ opacity: 0, x: -100, rotate: -5 }}
                  transition={{ type: "spring", stiffness: 300, damping: 25 }}
                  drag="x"
                  dragConstraints={{ left: 0, right: 0 }}
                  dragElastic={0.7}
                  onDragEnd={(_, { offset, velocity }: PanInfo) => {
                    if (selected !== null && (offset.x < -100 || offset.x > 100 || Math.abs(velocity.x) > 500)) {
                      next();
                    }
                  }}
                >
                  <div
                    className="card-doodles"
                    aria-hidden="true"
                  />
                  <p className="eyebrow">
                    {topic} • Mission {current + 1}
                  </p>
                  <p className="prompt">{question.prompt}</p>
                  <Visual type={question.visual} />
                  <div className="equation">
                    {question.equation}
                  </div>
                  <div
                    className="answers"
                    aria-label="Choose an answer"
                  >
                    {question.answers.map((answer, index) => {
                      const answerIsSelected = selected === answer;
                      return (
                        <button
                          key={answer}
                          className={`answer answer-${index + 1}${answerIsSelected ? " selected" : ""}`}
                          onClick={() => handleSelectAnswer(answer)}
                          aria-label={`Answer ${answer}`}
                        >
                          {answer}
                        </button>
                      );
                    })}
                  </div>
                  <button
                    className="next-button"
                    disabled={selected === null}
                    onClick={next}
                  >
                    {current === dynamicQuestions.length - 1
                      ? "Finish"
                      : "Next card"}{" "}
                    <span>→</span>
                  </button>
                </motion.article>
              </AnimatePresence>
            </div>
          </section>
        </main>
      )}
    </div>
  );
}

export default NonImprovementSection;
