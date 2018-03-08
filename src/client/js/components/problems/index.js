import Vue from 'vue';
import html from './index.pug';
import './index.css';
import sleep from 'sleep-promise';
import store, {userLogin, getUser} from 'js/store';

export default Vue.extend({
    data() {
        return { 
            problems: [ ],
        };
    },
    store,
    vuex: {
        actions: {
            userLogin,
        },
        getters: {
            user: getUser,
        }
    },
    methods:{
        getQuota(res){
            if(!res)return 5;
            if(String(new Date(Date.now())).substr(0,15) != String(new Date(res.last_submission)).substr(0,15)) return 5;
            return res.quota;
        },
        getProbId(prob) {
            return prob.problem_id; 
        },
        checkProbId(pid) {
            return { problem_id : id => id==pid }; 
        },
        async updateData(){
            clearInterval(this.timer);
            this.problems = (await this.$http.get('/problem/')).data; 
            const result = (await this.$http.get('/user/me')).data;
            if (result.login) {
                this.userLogin(result.user);
            }
            if(!_.isNil(this.timer))
                this.timer = setInterval(updateData, 2000);
        },
    },
    template: html,
    beforeDestroy(){
        clearInterval(this.timer);
        this.timer=null;
    },
    async ready() {
        this.problems = (await this.$http.get('/problem/')).data; 
        this.timer = setInterval(this.updateData, 2000);
    },
});
