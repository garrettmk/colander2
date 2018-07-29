import React from "react";
import { Form, Select } from "semantic-ui-react";
import _ from "lodash";

import Colander from "./colander";


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export class ObjectSelector extends React.Component {

    constructor (props) {
        super(props);

        this.fetchOptions = this.fetchOptions.bind(this);

        this.state = {
            loading: true,
            options: []
        }
    }

    componentDidMount () { this.fetchOptions() }
    componentDidUpdate (prevProps) {
        if (prevProps.type !== this.props.type
            || _.isEqual(prevProps.query, this.props.query))
            this.fetchOptions();
    }

    fetchOptions () {
        const { type, query } = this.props;

        this.setState({ loading: true, options: [] });
        Colander.filter(type, {
            query,
            view: { _only: ['id', 'name', 'title'] },
            onSuccess: results => {
                this.setState({
                    loading: false,
                    options: results.items.map(obj => ({ value: obj.id, text: obj.name || obj.title || `${type} #${obj.id}`}))
                })
            },
            onFailure: error => {
                alert(error);
                this.setState({ loading: false })
            }
        })
    }

    render () {
        const {form, ...childProps} = this.props;

        if (form)
            return <Form.Dropdown
                selection
                {...this.state}
                {...childProps}
            />;
        else
            return <Select
                {...this.state}
                {...childProps}
            />;
    }

}


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export class ExtensionSelector extends React.Component {

    constructor (props) {
        super(props);

        this.state = {
            loading: true,
            options: []
        }
    }

    componentDidMount () {
        Colander.filter('extension', {
            view: { _only: ['id', 'name'] },
            onSuccess: results => {
                this.setState({
                    loading: false,
                    options: results.items.map(ext => {return {text: ext.name, value: ext.id}})
                })
            },
            onFailure: error => {
                alert(error);
                this.setState({ loading: false })
            }
        })
    }

    render () {
        const { form, ...childProps } = this.props;

        if (form)
            return <Form.Dropdown
                selection
                {...this.state}
                {...childProps}
            />;
        else
            return <Select
                options={this.state.extensions}
                {...this.state}
                {...childProps}
            />
    }
}


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export class ActionSelector extends React.Component {

    constructor (props) {
        super(props);
        this.fetchActions = this.fetchActions.bind(this);

        this.state = {
            loading: true,
            options: []
        }
    }

    componentDidMount () { this.fetchActions(); }
    componentDidUpdate (prevProps) { this.props.extId !== prevProps.extId ? this.fetchActions() : null }

    fetchActions () {
        this.setState({ loading: true });
        const { extId } = this.props;

        Colander.filter('extension', {
            query: { id: extId },
            view: { _only: ['exports'] },

            onSuccess: results => {
                this.setState({
                    loading: false,
                    options: Object.keys(results.items[0].exports).map(exp => {
                        return { text: exp, value: exp }
                    })
                })
            },

            onFailure: error => {
                this.setState({ loading: false });
                alert(error);
            }
        });
    }

    render () {
        const { form, extId, ...childProps } = this.props;

        if (form)
            return <Form.Dropdown
                selection
                {...this.state}
                {...childProps}
            />;
        else
            return <Select
                {...this.state}
                {...childProps}
            />
    }
}


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export class VendorSelector extends React.Component {

    constructor (props) {
        super(props);

        this.state = {
            loading: false,
            options: []
        }
    }

    componentDidMount () {
        Colander.filter('vendor', {
            view: { _only: ['id', 'name'] },

            onSuccess: results => {
                this.setState({
                    loading: false,
                    options: results.items.map(vnd => { return {text: vnd.name, value: vnd.id} })
                })
            },

            onFailure: error => {
                this.setState({ loading: false });
                alert(error);
            }
        })
    }

    render () {
        const { form, ...childProps } = this.props;

        if (form)
            return <Form.Dropdown
                selection
                {...this.state}
                {...childProps}
            />;
        else
            return <Select
                {...this.state}
                {...childProps}
            />;
    }
}


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


const selectors = {
    'Extension': ExtensionSelector,
    'Action': ActionSelector,
    'Vendor': VendorSelector
};

export default selectors;