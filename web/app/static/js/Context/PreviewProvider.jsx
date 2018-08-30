import React from "react";
import PropTypes from "prop-types";

import { DocumentProvider } from "./DocumentContext";
import Colander from "../colander";


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////



export class PreviewProvider extends React.Component {

    constructor (props) {
        super(props);

        this.fetchPreview = this.fetchPreview.bind(this);

        this.state = {
            preview: undefined,
            loading: false
        }
    }

    componentDidMount () { this.fetchPreview() }
    componentDidUpdate (prevProps) {
        if (prevProps.type !== this.props.type
            || prevProps.id !== this.props.id)
            this.fetchPreview();
    }

    fetchPreview () {
        const { type, id } = this.props;

        if (!type || !id)
            return this.setState({ loading: false, preview: undefined });

        this.setState({ loading: true, preview: undefined });

        Colander.filter(type, {
            query: { id },
            schema: 'Preview',

            onSuccess: results => this.setState({
                loading: false,
                preview: results.items ? results.items[0] : undefined
            }),

            onFailure: error => { this.setState({
                loading: false,
                preview: undefined
            }); alert(error) }
        })
    }

    render () {
        const {type, id, children, ...extras} = this.props;
        const params = {type, id, ...this.state, ...extras};
        return (
            <DocumentProvider {...params}>
                {children}
            </DocumentProvider>
        )
    }
}


PreviewProvider.propTypes = {
    type: PropTypes.string,
    id: PropTypes.number
};

