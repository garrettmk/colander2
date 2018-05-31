import React from "react";
import { withRouter } from "react-router-dom";


class SearchBox extends React.Component {

    constructor (props) {
        super(props);
        this.state = {
            input: this.props.input || ''
        };

        this.handleInputChange = this.handleInputChange.bind(this);
        this.handleSearch = this.handleSearch.bind(this);
    }

    handleInputChange (e) {
        const value = e.target.value;
        this.setState({
            input: value
        })
    }

    handleSearch () {
        const queryString = '?query=' + encodeURIComponent(this.state.input)
        this.props.history.push('/search' + queryString)
    }

    render () {
        return (
            <div>
                <input
                    id={'searchInput'}
                    type="text"
                    placeholder={"Search"}
                    value={this.state.input}
                    onChange={this.handleInputChange}
                />
                <button onClick={this.handleSearch}>Search</button>
            </div>
        );
    }
}

export default withRouter(SearchBox);