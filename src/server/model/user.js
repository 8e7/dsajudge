import mongoose from 'mongoose';
import _ from 'lodash';
import Problem from '/model/problem';
const Schema = mongoose.Schema;

const userSchema = Schema({
  email: {
    type: String,
    index: true,
    unique: true
  },
  password: {
    type: String,
    required: true
  },
  ssh_key: String,
  git_upload_key: String,
  accountType: {
    type: String,
    required: true,
    default: 'User'
  },
  meta: {
    name: String,
    id: String
  },
  submission_limit: [{
    problem_id: Number,
    last_submission: Date,
    quota: Number
  }],
  roles: [String],
  homeworks: [{
    homework_id: Number,
    file_name: String,
    file_size: String,
    file_sha1: String
  }],
  groups: [String]
}, {usePushEach: true});

userSchema.methods.hasRole = function (role) {
  const roles = this.roles;
  if (!roles) return false;
  return _.includes(roles, role);
};

userSchema.methods.isAdmin = function () {
  return this.hasRole('admin');
};

userSchema.methods.isTA = function () {
  return this.hasRole('TA');
};

// TODO: There may have some race condition in checkQuota. It may cause user breakthrough the quota limit.
userSchema.methods.checkQuota = async function (pid) {
  const problem = await Problem.findOne({ _id: pid });
  if (!problem) return false;
  const limit = this.submission_limit;
  let filter_res = _.filter(limit, _.conforms({ problem_id: id => id == pid }));
  let res;
  const today = new Date(Date.now());

  if (filter_res === undefined || filter_res.length == 0) {
    res = {
      problem_id: pid,
      last_submission: today,
      quota: 0
    };
    this.submission_limit.push(res);
    filter_res = _.filter(this.submission_limit, _.conforms({ problem_id: id => id == pid }));
  }
  res = filter_res[0];
  console.log(String(today), String(res.last_submission), this.email);
  if (String(today).substr(0, 15) != String(res.last_submission).substr(0, 15)) {
    res.quota = 0;
    res.last_submission = today;
  }
  if (res.quota >= problem.quota) {
    return false;
  } else {
    res.quota += 1;
    await this.save();
    return true;
  }
};
const User = mongoose.model('User', userSchema);
export default User;
