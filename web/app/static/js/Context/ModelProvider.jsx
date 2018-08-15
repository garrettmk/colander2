import React from "react";
import PropTypes from "prop-types";
import update from "immutability-helper";
import _ from "lodash";

import { EditableDocProvider } from "./DocumentContext";
import Colander from "../colander";


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export class ModelProvider extends React.Component {

    constructor (props) {
        super(props);

        this.fetchModel = this.fetchModel.bind(this);
        this.handleSave = this.handleSave.bind(this);

        this.state = {
            doc: undefined,
            schemas: {},
            errors: {},
            loading: false
        }
    }

    componentDidMount () { this.fetchModel() }
    componentDidUpdate (prevProps) {
        if (prevProps.type !== this.props.type
            || prevProps.id !== this.props.id
            || !_.isEqual(prevProps.view, this.props.view))
            this.fetchModel();
    }

    fetchModel () {
        const { type, id, view } = this.props;

        if (!type || !id)
            return this.setState({ loading: false, doc: undefined, schemas: {}, errors: {} })

        this.setState({ loading: true });

        Colander.filter(type, {
            query: { id },
            view,

            onSuccess: results => this.setState({
                loading: false,
                doc: results.items ? results.items[0] : undefined,
                schemas: results.schema ? results.schema.definitions : {},
            }),

            onFailure: error => { this.setState({
                loading: false,
                doc: undefined,
                schemas: {},
            }); alert(error) }
        })
    }

    handleSave (edits) {
        this.setState({ loading: true });
        const { type, id } = this.props;
        const { doc } = this.state;

        Colander.update(type, {
            query: { id },
            data: edits,

            onSuccess: results => this.setState({
                loading: false,
                doc: results.errors ? doc : update(doc, {$merge: edits}),
                edits: results.errors ? edits : {},
                errors: results.errors || {},
            }),

            onFailure: error => { this.setState({
                loading: false,
            }); alert(error) }
        })
    }

    render () {
        const { type } = this.props;

        return (
            <EditableDocProvider {...this.state} type={type} onSave={this.handleSave}>
                {this.props.children}
            </EditableDocProvider>
        )
    }
}


ModelProvider.propTypes = {
    type: PropTypes.string,
    id: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
    view: PropTypes.object
};


ModelProvider.defaultProps = {
    view: {}
};


