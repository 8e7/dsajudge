import mongoose from 'mongoose';
import autoIncrement from './autoIncrement';

const Schema = mongoose.Schema;

const schema = Schema({
  name: {
    type: String,
    required: true,
    default: 'A Brand New Problem'
  },
  visible: {
    type: Boolean,
    required: true,
    default: false
  },
  timeLimit: {
    type: Number,
    default: 1
  },
  memLimit: {
    type: Number,
    default: (1 << 20)
  },
  quota: {
    type: Number,
    default: 5
  },
  hasSpecialJudge: {
    type: Boolean,
    default: false
  },
  notGitOnly: {
    type: Boolean,
    default: false
  },
  showStatistic: {
    type: Boolean,
    default: false
  },
  showDetailSubtask: {
    type: Boolean,
    default: true
  },
  testdata: {
    count: Number,
    points: Number,
    groups: [{
      count: Number,
      points: Number,
      tests: [String]
    }]
  },
  testFiles: [String],
  resource: [String],
  compileEXArg: [String],
  compileEXHeader: [String],
  compileEXFile: [String],
  compileEXLink: [String]
});

schema.plugin(autoIncrement.plugin, 'Problem');
const Problem = mongoose.model('Problem', schema);
export default Problem;
