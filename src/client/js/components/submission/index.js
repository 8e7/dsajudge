import Vue from 'vue';
import html from './index.pug';
import './index.css';
import sleep from 'sleep-promise';
import probUtils from 'js/mixins/probUtils';


export default Vue.extend({
    mixins: [probUtils],
    data() {
        return { 
            id: null,
            submission: null,
            showResult: false,
            sourceCode: null,
        };
    },
    template: html,
    ready() {
        this.id = this.$route.params.id;
        this.fetch();
        this.fetchSrc();
    },
    methods: {
        async fetch() {
            await this.getSubmission();

            while (this.submission.status === 'pending' || this.submission.status === 'judging') {
                await sleep(2000);
                await this.getSubmission();
            }
            
        },
        async fetchSrc() {
            let result;
            try {
                result = await this.$http.get(`/submission/sourceCode/${this.id}`);
            } catch(e) {
                console.log(e);
            }
            const editor = ace.edit('editor');
            const session = editor.getSession();
            session.setValue(result.data);
            session.setMode('ace/mode/c_cpp');
            editor.setReadOnly(true);
        },
        async getSubmission() {
            let _result;
            try {
                _result = await this.$http.get(`/submission/${this.id}`);
            } catch(e) {
                console.log(e);
            }
            const data = _result.data; 
            if (data._result) {
                const transform = x => {
                    if (!x.result) {
                        x.result = 'Judging';
                        x.points = x.runtime = '?';
                    } else {
                        x.result = this.probUtils.toHumanString(x.result);
                        x.runtime = this.probUtils.toDisplayTime(x.runtime);
                    }
                };
                data._result.subresults.forEach(x => {
                    transform(x);
                    x.subresults.forEach(y => transform(y));
                });
            }
            this.submission = data;
            this.showResult = (this.submission 
                && this.submission.status !== 'pending' 
                && this.submission.result !== 'CE');
        }
    },
});

