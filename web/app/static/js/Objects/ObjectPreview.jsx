import React from "react";
import { withRouter } from "react-router-dom";
import PropTypes from "prop-types";

import { Item, Button, Modal, Icon, Popup } from "semantic-ui-react";

import { DocumentContext } from "../Contexts";
import { ObjectSearchBox } from "../Objects";
import { defaultImage, defaultImages } from "../style";


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


const noWrapStyle = {
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis'
};


class _ObjectPreview extends React.Component {

    constructor (props) {
        super(props);

        this.handleSearch = this.handleSearch.bind(this);
        this.handleResultSelect = this.handleResultSelect.bind(this);

        this.state = { searching: false }
    }

    handleSearch () { this.setState({ searching: true })};

    handleResultSelect (result) {
        const { onChange } = this.props;
        if (onChange) onChange(result.id);
        this.setState({ searching: false });
    }

    render () {
        const { small, onChange} = this.props;
        const { searching } = this.state;

        return (
            <DocumentContext.Consumer>
                { ({ preview, type }) => (
                    <React.Fragment>
                        <Item.Group link onClick={() => preview && this.props.history.push(`/${type}/${preview.id}`)}>
                            <Item>
                                <Item.Image size={small ? 'mini' : 'small'} src={preview
                                    ? preview.image
                                        ? preview.image
                                        : defaultImages[type].light
                                    : defaultImage.light
                                }/>

                                <Item.Content style={{ position: 'relative' }}>

                                    {onChange
                                        ? <Popup
                                            hoverable
                                            trigger={<Icon
                                                circular
                                                size={'small'}
                                                name={'search'}
                                                onClick={this.handleSearch}
                                                style={{
                                                    position: 'absolute',
                                                    right: '0px',
                                                    top: '-3px',
                                                }}
                                            />}
                                        >
                                            <Button icon={'search'} onClick={this.handleSearch}/>
                                        </Popup>

                                        : <React.Fragment/>
                                    }

                                     <Item.Header className={small ? 'ui tiny' : ''} style={noWrapStyle}>
                                         {preview
                                            ? preview.title
                                                ? preview.title
                                                : 'n/a'
                                            : 'None selected'
                                         }
                                     </Item.Header>



                                    <Item.Meta style={noWrapStyle}>
                                        {preview
                                            ? preview.description
                                            : 'Click to search...'
                                        }
                                    </Item.Meta>

                                </Item.Content>
                            </Item>
                        </Item.Group>
                        <Modal basic size={'tiny'} open={searching}>
                            <Modal.Header>Select Object</Modal.Header>
                            <Modal.Content>
                                <ObjectSearchBox
                                    fluid
                                    input={{fluid: true}}
                                    type={type}
                                    onResultSelect={this.handleResultSelect}
                                />
                            </Modal.Content>
                            <Modal.Actions>
                                <Button
                                    basic
                                    inverted
                                    negative
                                    color={'red'}
                                    icon={'remove'}
                                    onClick={() => this.handleResultSelect({ id: null })}
                                    content={'Clear Selection'}
                                />
                                <Button
                                    basic
                                    inverted
                                    color={'grey'}
                                    icon={'cancel'}
                                    onClick={() => this.setState({ searching: false })}
                                    content={'Cancel'}
                                />
                            </Modal.Actions>
                        </Modal>
                    </React.Fragment>
                )}
            </DocumentContext.Consumer>
        )
    }
}

export const ObjectPreview = withRouter(_ObjectPreview);


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


ObjectPreview.propTypes = {
    small: PropTypes.bool,
    onChange: PropTypes.func,
};
