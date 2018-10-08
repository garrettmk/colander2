import React from "react";
import PropTypes from "prop-types";
import _ from "lodash";
import update from "immutability-helper";
import Colander from "../colander";


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


const ExtensionContext = React.createContext({
    extension: {},
    trackers: [],
    errors: [],
    send: undefined,
    dismissError: undefined,
    dismissTracker: undefined,
    closeTracker: () => {}
});


export default ExtensionContext;


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export class ExtensionProvider extends React.Component {

    constructor (props) {
        super(props);

        this.resetState = this.resetState.bind(this);
        this.fetchExtension = this.fetchExtension.bind(this);
        this.send = this.send.bind(this);
        this.dismissError = this.dismissError.bind(this);
        this.dismissTracker = this.dismissTracker.bind(this);
        this.closeTracker = this.closeTracker.bind(this);

        this.state = {
            extension: {},
            instances: [],
            errors: []
        }
    }

    resetState () {
        this.setState({
            extension: {},
            instances: [],
            errors: []
        })
    }

    componentDidMount () {
        this.fetchExtension();
    }

    componentDidUpdate (prevProps, prevState) {
        if (prevProps.extId !== this.props.extId)
            this.fetchExtension();
    }

    fetchExtension () {
        const { extId } = this.props;

        if (!extId)
            return this.resetState();

        Colander.filter('Extension', {
            query: { id: extId },

            onSuccess: results => this.setState({
                extension: results.items[0],
                instances: [],
                errors: []
            }),

            onFailure: error => {
                this.resetState();
                alert(error);
            }
        })
    }

    send({ action, context, name }) {
        const { extId } = this.props;

        Colander.create('TaskInstance', {
            data: {
                extension_id: extId,
                action: action,
                data: context,
                name: name,
                status: 'running'
            },

            onSuccess: results => {
                if (results.errors)
                    this.setState(prevState => update(prevState, { errors: {$push: [results.errors]} }));
                else
                    this.setState(prevState => update(prevState, { instances: {$push: [results.id]} }))
            },

            onFailure: error => this.setState(prevState => update(prevState, { errors: {$push: [error.toString()]} }))
        })
    }

    dismissError (idx) {
        this.setState(prevState => update(prevState, { errors: { $splice: [[idx, 1]] } }));
    }

    dismissTracker (idx) {
        this.setState(prevState => update(prevState, { instances: { $splice: [[idx, 1]] } }));
    }

    closeTracker (id) {
        const idx = this.state.instances.indexOf(id);
        if (idx !== -1 )
            this.dismissTracker(idx);

        Colander.delete_('TaskInstance', {
            query: { id: id },
            onSuccess: results => results.errors ? alert(results.errors) : null,
            onFailure: error => alert(error)
        });
    }

    render () {
        return (
            <ExtensionContext.Provider value={{
                ...this.state,
                send: this.send,
                dismissError: this.dismissError,
                dismissTracker: this.dismissTracker,
                closeTracker: this.closeTracker,
            }}>
                {this.props.children}
            </ExtensionContext.Provider>
        )
    }
}

ExtensionProvider.propTypes = {
    extId: PropTypes.number
};