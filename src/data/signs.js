// Simple demo sign list; extend or replace with your own.
const signs = [
  {
    id: 'hello',
    word: 'HELLO',
    meaning: 'A friendly greeting.',
    tips: 'Open hand by your temple and move outward in a small wave.',
    sampleImage: '/assets/sign-examples/hello.svg',
    expectedOpenHand: true,
  },
  {
    id: 'thankyou',
    word: 'THANK YOU',
    meaning: 'Expression of gratitude.',
    tips: 'Open hand from chin outward.',
    sampleImage: '/assets/sign-examples/thankyou.svg',
    expectedOpenHand: true,
  },
  {
    id: 'yes',
    word: 'YES',
    meaning: 'Affirmation.',
    tips: 'Make a fist and nod it up and down.',
    sampleImage: '/assets/sign-examples/yes.svg',
    expectedOpenHand: false,
  },
  {
    id: 'no',
    word: 'NO',
    meaning: 'Negation.',
    tips: 'Bring index and middle finger to thumb like a talking mouth.',
    sampleImage: '/assets/sign-examples/no.svg',
    expectedOpenHand: false,
  },
];

export default signs;
