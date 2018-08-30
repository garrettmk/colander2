import React from "react";
import PropTypes from "prop-types";
import _ from "lodash";

import { CollectionContext } from "./CollectionContext";
import Colander from "../colander";


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export class SimilarProvider extends React.Component {

    constructor (props) {
        super(props);

        this.fetchMatches = this.fetchMatches.bind(this);

        this.state = {
            loading: false,
            items: [],
            schemas: {},
            total: undefined,
            page: undefined,
            pages: undefined,
            per_page: undefined,
        }
    }

    componentDidMount () { this.fetchMatches() }
    componentDidUpdate (prevProps, prevState) {
        const { id, view } = this.props;

        if (prevProps.id !== id
            || !_.isEqual(prevProps.view, view))
            this.fetchMatches();
    }

    fetchMatches () {
        this.setState({ loading: true });
        const { id, view } = this.props;

        Colander.similar(id, {
            onSuccess: results => this.setState({
                ...results,
                schemas: results.schema ? results.schema.definitions : {},
                loading: false,
            }),

            onFailure: error => this.setState({
                loading: false
            })
        })
    }

    render () {
        const { children } = this.props;

        return (
            <CollectionContext.Provider value={{
                ...this.state,
                type: 'Listing'
            }}>
                {children}
            </CollectionContext.Provider>
        )
    }
}


SimilarProvider.propTypes = {
    id: PropTypes.number,
    view: PropTypes.object,
};


SimilarProvider.defaultProps = {
    view: {}
};