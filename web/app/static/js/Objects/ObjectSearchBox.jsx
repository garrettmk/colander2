import React from "react";
import PropTypes from "prop-types";
import _ from "lodash";

import { Search } from "semantic-ui-react";

import Colander from "../colander";


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export class ObjectSearchBox extends React.Component {

    constructor (props) {
        super(props);

        this.fetchResults = _.debounce(this.fetchResults.bind(this), 300, {trailing: true});
        this.handleQueryChange = this.handleQueryChange.bind(this);
        this.handleResultSelect = this.handleResultSelect.bind(this);

        this.state = {
            query: '',
            loading: false,
            results: {}
        }
    }

    componentDidUpdate (prevProps, prevState) {
        if (!_.isEqual(prevProps.type, this.props.type)
            || prevState.query !== this.state.query)
            this.fetchResults();
    }

    fetchResults () {
        this.setState({ loading: true });

        const { type } = this.props;
        const { query } = this.state;

        Colander.preview({
            type,
            query,

            onSuccess: results => this.setState({ loading: false, results }),
            onFailure: error => this.setState({ loading: false })
        })
    }

    handleQueryChange (e, { value }) {
        if (!value)
            return this.setState({ query: '', loading: false, results: [] });
        this.setState({ query: value });
    }

    handleResultSelect (e, { result }) {
        const { onResultSelect } = this.props;
        if (onResultSelect)
            onResultSelect(result);
    }

    render () {
        const { type, onResultSelect, ...boxProps } = this.props;
        const { query, loading, results } = this.state;
        return (
            <Search
                category
                loading={loading}
                onSearchChange={this.handleQueryChange}
                onResultSelect={this.handleResultSelect}
                results={results}
                value={query}
                {...boxProps}
            />
        )
    }
}


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


ObjectSearchBox.propTypes = {
    type: PropTypes.string,
    onResultSelect: PropTypes.func,
};

