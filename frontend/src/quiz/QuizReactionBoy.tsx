export function QuizReactionBoy({ correct }: { correct: boolean }) {
  return <svg
    className={`quiz-reaction-boy ${correct ? 'is-happy' : 'is-encouraging'}`}
    viewBox="0 0 120 140"
    role="presentation"
    aria-hidden="true"
    focusable="false"
  >
    <ellipse className="quiz-reaction-shadow" cx="60" cy="132" rx="30" ry="5" fill="#594b71" opacity=".16" />
    <g className="quiz-reaction-figure">
      <path d={correct ? 'M43 97 34 119 44 123 57 101M76 97 87 119 77 123 64 101' : 'M43 98 40 121 51 123 57 102M75 98 79 121 68 123 63 102'} fill="#374286" stroke="#30396f" strokeWidth="3" strokeLinejoin="round" />
      <path d={correct ? 'M35 119 44 121 48 129 31 129Q28 125 35 119ZM77 121 86 119Q93 124 90 129H73Z' : 'M40 119 51 121 53 129H35Q33 124 40 119ZM68 121 79 119Q86 123 84 129H66Z'} fill="#ef754e" stroke="#c95140" strokeWidth="2" />
      <path d={correct ? 'M34 125H46M76 125H89' : 'M37 125H51M68 125H82'} stroke="#fff4df" strokeWidth="2" strokeLinecap="round" />
      <path d="M47 99Q60 106 74 99" fill="none" stroke="#27356e" strokeWidth="3" strokeLinecap="round" />
      <path d="M43 67 Q60 59 77 67 L83 101 Q60 111 37 101Z" fill="#5c65e8" stroke="#454ec0" strokeWidth="3" />
      <path d="M50 66 60 74 69 66M60 74V96" fill="none" stroke="#d7dcff" strokeWidth="2" strokeLinejoin="round" />
      <path d="M48 88Q60 92 73 88" fill="none" stroke="#454ec0" strokeWidth="2" />
      <circle cx="70" cy="78" r="5" fill="#ffcc55" stroke="#e6a42b" strokeWidth="1.5" />
      <path d="m70 75 1 2h2l-2 1.5.5 2-1.5-1-2 1 .5-2-1.5-1.5h2Z" fill="#fff7df" />
      <path d={correct ? 'M43 75 23 52 15 60 36 87M77 75 97 52 105 60 84 87' : 'M43 75 29 96 36 102 49 87M77 75 91 96 84 102 71 87'} fill="#bb754f" stroke="#945a3b" strokeWidth="3" strokeLinejoin="round" />
      <path d="M36 78 43 83M77 83 84 78" stroke="#d7dcff" strokeWidth="3" strokeLinecap="round" />
      <circle cx={correct ? 17 : 32} cy={correct ? 55 : 99} r="6" fill="#bb754f" />
      <circle cx={correct ? 103 : 88} cy={correct ? 55 : 99} r="6" fill="#bb754f" />
      <path d={correct ? 'M14 53 13 48M18 50 18 46M102 50 102 46M106 53 107 48' : 'M30 97 28 92M34 94 34 90M86 94 86 90M90 97 92 92'} fill="none" stroke="#945a3b" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M52 62V72Q60 79 68 72V62" fill="#bb754f" />
      <ellipse cx="32" cy="47" rx="5" ry="8" fill="#c9865d" stroke="#945a3b" strokeWidth="1.5" />
      <ellipse cx="88" cy="47" rx="5" ry="8" fill="#c9865d" stroke="#945a3b" strokeWidth="1.5" />
      <ellipse cx="60" cy="43" rx="29" ry="30" fill="#c9865d" stroke="#945a3b" strokeWidth="2" />
      <path d="M31 42Q29 13 54 12Q62 5 72 12Q91 13 90 39Q79 32 75 22Q61 36 41 32Z" fill="#33283d" />
      <path d="M39 20Q50 11 61 15M65 14Q77 15 83 28" fill="none" stroke="#5a465a" strokeWidth="3" strokeLinecap="round" />
      <path d="M49 12 46 7M66 10 68 5" fill="none" stroke="#33283d" strokeWidth="3" strokeLinecap="round" />
      <path d="M42 35Q47 32 51 36M69 36Q74 32 79 35" fill="none" stroke="#33283d" strokeWidth="2.5" strokeLinecap="round" />
      <ellipse cx="48" cy="44" rx="2.5" ry="3.5" fill="#33283d" />
      <ellipse cx="73" cy="44" rx="2.5" ry="3.5" fill="#33283d" />
      <circle cx="47" cy="43" r=".9" fill="#fff" />
      <circle cx="72" cy="43" r=".9" fill="#fff" />
      <path d="M59 46Q57 51 61 51" fill="none" stroke="#a86448" strokeWidth="1.5" strokeLinecap="round" />
      {correct ? <>
        <path d="M49 55Q60 69 72 55Z" fill="#fff" stroke="#8b3f42" strokeWidth="2" strokeLinejoin="round" />
        <circle cx="41" cy="53" r="4" fill="#e9977d" opacity=".6" />
        <circle cx="79" cy="53" r="4" fill="#e9977d" opacity=".6" />
      </> : <>
        <path d="M51 61Q60 54 69 61" fill="none" stroke="#743e42" strokeWidth="2.5" strokeLinecap="round" />
        <path d="M40 27 49 30M71 30 80 27" fill="none" stroke="#33283d" strokeWidth="2" strokeLinecap="round" />
      </>}
    </g>
    {correct && <g className="quiz-reaction-stars" fill="#f1aa19">
      <path d="M17 23 19 17 21 23 27 25 21 27 19 33 17 27 11 25Z" />
      <path d="M98 20 100 14 102 20 108 22 102 24 100 30 98 24 92 22Z" />
    </g>}
  </svg>
}
